# -*- coding: utf-8 -*-
import json

class AnalyzeCompare:
    def __init__(self, analyze, compared_value):
        self.compared_value = compared_value
        self.analyze = analyze
        
    def is_present(self):
        return not self.compared_value == None 
        
    def is_upper(self):
        return self.compared_value > 0
        
    def is_lower(self):
        return self.compared_value < 0
        
    def is_norm(self):
        return self.compared_value == 0
        
    def get_template(self):
        return 'forms/analyze/' + self.analyze.edit_template + '.html'

class Norm:
    def __init__(self, norm, sex=None, age_from=None, age_to=None):
        self.sex = sex
        self.age_to = age_to
        self.age_from = age_from
        self.norm = norm

class AnalyzeNorms:
    def __init__(self, *norms):
        self.norms = norms
        
    def get_norm(self, sex, age):
        res = filter(lambda x: (not x.sex or x.sex == sex) and (not x.age_to or age <= x.age_to) and (not x.age_from or age > x.age_from), self.norms)
        if len(res) >= 0:
            return res[0].norm
            
        return None
    
    def compare_value(self, sex, age, value):
        norm = self.get_norm(sex, age)
        
        if not norm:
            return 0
        
        if value < norm[0]:
            return -1
            
        if value > norm[1]:
            return 1
        
        return 0

class Analyze:
    def __init__(self, key, title, units, edit_template, norms):
        self.key = key
        self.title = title
        self.edit_template = edit_template
        self.norms = norms
        self.units = units
    
    def format_value(self, value):
        return "%g %s" % (self.get_value(value), self.units)
        
    def get_value(self, raw_value):
        try: 
            value = float(raw_value) 
        except Exception:
            value = 0
        
        return value

FE = Analyze("Fe", u"Железо", u"мкмоль/лЭ", "fe", AnalyzeNorms(
        Norm((13, 30), "male", 14),
        Norm((12, 25), "female", 14),
        Norm((9, 21.5), None, 0.083, 14),
        Norm((14.8, 17.8), age_to=0.083)
    )
)

Ferritin = Analyze("Ferritin", u"Ферритин", u"мкг/л", "ferritin", AnalyzeNorms(
        Norm((20, 250), "male", 14),
        Norm((10, 120), "female", 14),
        Norm((6, 320), None, 5, 14),
        Norm((6, 60), None, 1, 5),
        Norm((6, 80), None, 0.5, 1),
        Norm((6, 410), None, 0.083, 0.5),
        Norm((25, 400), age_to=0.083)
    )
)

SRB = Analyze("SRB", u"СРБ", u"мг/л", "srb", AnalyzeNorms(
        Norm((0, 5))
    )
)

COE = Analyze("COE", u"КОЕ", u"мм/час", "coe", AnalyzeNorms(
        Norm((2, 10), "male"),
        Norm((2, 15), "female")
    )
)

Ret = Analyze("Ret", u"Ретикулоциты", u"%", "ret", AnalyzeNorms(
        Norm((0.2, 1.2))
    )
)
    
WBC = Analyze("WBC", u"ВБЦ", u"10^9/л", "wbc", AnalyzeNorms(
        Norm((4, 9))
    )
)
    
RBC = Analyze("RBC", u"РБЦ", u"10^12/л", "rbc", AnalyzeNorms(
        Norm((4, 5), "male"),
        Norm((3.8, 4.5), "female")
    )
)

PLT = Analyze("PLT", u"ПЛТ", u"10^9/л", "plt",  AnalyzeNorms(
        Norm((150, 400))
    )
)

MCV = Analyze("MCV", u"МЦВ", u"фл", "mcv",  AnalyzeNorms(
        Norm((80, 100))
    )
)

class NoValueAnalyze(Analyze):
    def __init__(self, key, title, edit_template):
        Analyze.__init__(self, key, title, "", edit_template, AnalyzeNorms( Norm((0,0))))
    
    def format_value(self, value):
        value = self.get_value(value)
        
        if value > 0:
            return u'↑'
        
        if value < 0:
            return u'↓'
            
        return u'N'

B12 = NoValueAnalyze("B12", u"B12", "b12")
    
Folats = NoValueAnalyze("Folats", u"Фолаты", "folats")

class FractGAnalyze(Analyze):
    def __init__(self, key, title, edit_template):
        Analyze.__init__(self, key, title, "", edit_template, AnalyzeNorms())
        
    def get_value(self, raw_value):
        try: 
            value = json.loads(raw_value)
        except Exception:
            value = {u'a':'',u'a2':'',u'f':'',u's':'',u'anom':''}
        
        return value
    
    def format_value(self, value):
        value = self.get_value(value)
        items = filter(lambda x: not x[0] == u'anom', value.items())
        items_strs = [item[0] + "=" + item[1] + "%" for item in items]
        anom = value[u'anom']
        if anom:
            items_strs.append(u"Аномальный ген: " + anom)

        return ", ".join(items_strs) 

FractG = FractGAnalyze("FractG", u"Фракции гемоглобина", "fract_gemoglob" )

analyze_list = [ 
    FE,
    Ferritin,
    SRB,
    COE,
    Ret,
    WBC,
    RBC,
    PLT,
    MCV,
    B12,
    Folats,
    FractG
]

analyzes_map = {analyze.key: analyze for analyze in analyze_list}

class UserAnalyzes:
    def __init__(self, user, analyze_value_map):
        self.user = user
        self.analyze_value_map = analyze_value_map
        
    def has_analyze(self, analyze_key):
        if self.analyze_value_map and analyze_key in self.analyze_value_map:
            return True
        return False
    
    def compare_value(self, analyze_key):
        analyze = analyzes_map[analyze_key]
        
        if not self.has_analyze(analyze_key):
            return AnalyzeCompare(analyze, None)
        try:
            value = float(self.analyze_value_map[analyze_key])
        except ValueError:
            value = -1
        
        compared_value = analyze.norms.compare_value( self.user.sex, self.user.get_age(), value )
        print(analyze.key, value, compared_value)
        
        return AnalyzeCompare(analyze, compared_value)