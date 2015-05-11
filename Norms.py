# -*- coding: utf-8 -*-
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
            return -1;
            
        if value > norm[1]:
            return 1;
        
        return 0;

class Analyze:
    def __init__(self, key, title, edit_template, norms):
        self.key = key
        self.norms = norms

FE = Analyze("Fe", "Железо", "fe", AnalyzeNorms(
        Norm((13, 30), "male", 14),
        Norm((12, 25), "female", 14),
        Norm((9, 21.5), None, 0.083, 14),
        Norm((17.8, 14.8), age_to=0.083)
    )
)

Ferritin = Analyze("Ferritin", "Ферритин", "ferritin", AnalyzeNorms(
        Norm((20, 250), "male", 14),
        Norm((10, 120), "female", 14),
        Norm((6, 320), None, 5, 14),
        Norm((6, 60), None, 1, 5),
        Norm((6, 80), None, 0.5, 1),
        Norm((6, 410), None, 0.083, 0.5),
        Norm((25, 400), age_to=0.083)
    )
)

SRB = Analyze("SRB", "СРБ", "srb", AnalyzeNorms(
        Norm((0, 5))
    )
)

COE = Analyze("COE", "КОЕ", "coe", AnalyzeNorms(
        Norm((2, 10), "male"),
        Norm((2, 15), "female")
    )
)

Ret = Analyze("Ret", "РЕТ", "ret", AnalyzeNorms(
        Norm((0.2, 1.2))
    )
)
    
WBC = Analyze("WBC", "ВБЦ", "", AnalyzeNorms(
        Norm((4, 9))
    )
)
    
RBC = Analyze("RBC", "РБЦ", "", AnalyzeNorms(
        Norm((4, 5), "male"),
        Norm((3.8, 4.5), "female")
    )
)

PLT = Analyze("PLT", "ПЛТ", "",  AnalyzeNorms(
        Norm((150, 400))
    )
)

MCV = Analyze("MCV", "МЦВ", "mcv",  AnalyzeNorms(
        Norm((80, 100))
    )
)

class AnalyzeHelper:
    def __init__(self, *analyzes):
        self.analyzes = {analyze.key: analyze for analyze in analyzes}
        
    def accept_analyze_map(self, analyze_value_map):
        self.analyze_value_map = analyze_value_map
        
    def has_analyze(self, analyze_key):
        if self.analyze_value_map and analyze_key in self.analyze_value_map:
            return True
        
        return False
        
    def compare_value(self, analyze_key, sex, age):
        value = int(self.analyze_value_map[analyze_key])
        analyze = self.analyzes[analyze_key]
        
        return analyze.norms.compare_value( sex, age, value )
        
analyze_helper = AnalyzeHelper(
    FE,
    Ferritin,
    SRB,
    COE,
    Ret,
    WBC,
    RBC,
    PLT,
    MCV
)

analyze_helper.accept_analyze_map({
    "Fe": "4"
    })
    
print(analyze_helper.compare_value("Fe", "male", 10))