# -*- coding: utf-8 -*-
import jinja2
import os
import webapp2
import datetime
import math
import json

from google.appengine.api import users
from google.appengine.ext import ndb
from Norms import UserAnalyzes 
from Norms import analyzes_map 

# We set a parent key on the 'Greetings' to ensure that they are all in the same
# entity group. Queries across the single entity group will be consistent.
# However, the write rate should be limited to ~1/second.

VALUE_DOWN = u"↓"
VALUE_UP = u"↑"
VALUE_N = u"N"

ndb.get_context().set_cache_policy(lambda key: key.kind() != 'PacientAnalyze')

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class Greeting(ndb.Model):
    author = ndb.UserProperty()
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)

class Pacient(ndb.Model):
    card_no = ndb.StringProperty()
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty(indexed=False)
    middle_name = ndb.StringProperty(indexed=False)
    birthday_date = ndb.DateTimeProperty(auto_now_add=False)
    sex = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    extra = ndb.StringProperty(indexed=False)
    cycle_faze = ndb.StringProperty(indexed=False)
    
    def get_age(self):
        days = (datetime.datetime.today() - self.birthday_date).days
        return math.floor(days / 365.2425)
        
    def get_formatted_age(self):
        days = (datetime.datetime.today() - self.birthday_date).days
        years = math.floor(days / 365.2425)
        
        if years < 1:
            months = math.floor(days / 30)
            return u"%d месяц" % months
        
        return u"%d лет" % years
        

class PacientAnalyze(ndb.Model):
    pacient_key = ndb.KeyProperty()
    #analyze_type = ndb.KeyProperty()
    analyze_type = ndb.StringProperty()
    analyze_value = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    
    def get_analyze(self):
        if self.analyze_type in analyzes_map:
            return analyzes_map[self.analyze_type]
        return None
        
    def get_analyze_title(self):
        analyze = self.get_analyze()
        if analyze:
            return analyze.title
        return "UNKNOWN"
        
    def get_formatted_value(self):
        analyze = self.get_analyze()
        if analyze:
            return analyze.format_value(self.analyze_value)
        return self.analyze_value

menu_items = [
        ("/cabinet",u'Личный кабинет' ),
        ("/pacients",u'Пациенты' ),
        ("/stats", u'Статистика'),
        # ("/about", u'О программе')
        ]

anonymouse_menu_items = [
        # ("/about", u'О программе')
        ]

class BaseAuthHandler(webapp2.RequestHandler):
    def get_logged_user(self):
        return users.get_current_user()

class AppPage(BaseAuthHandler):
    def get_template_context(self):
        context = {}

        user = {}
        if users.get_current_user():
            user['url'] = users.create_logout_url(self.request.uri)
            user['is_logged'] = True
            context['menu'] = self.get_menu(menu_items)
        else:
            user['url'] = users.create_login_url(self.request.uri)
            user['is_logged'] = False
            context['menu'] = self.get_menu(anonymouse_menu_items)

        context['user'] = user

        return context

    def get(self):
        template = jinja_environment.get_template(self.get_page_template())
        self.response.out.write(template.render(self.get_template_context()))

    def get_page_template(self):
        return 'page.html'

    def get_menu(self, menu_items):
        menu = []

        for url, title in menu_items:
            item = {
                    "url": url,
                    "title": title
                    }
            if self.request.uri.endswith(url):
                item["is_active"] = True
            menu.append(item)

        return menu

class PrivatePage(AppPage):
    def get(self):
        if not self.get_logged_user():
            self.abort(403)

        super(PrivatePage, self).get()
        
class HomePage(AppPage):
    def get_page_template(self):
        return 'home.html'

class PacientsPage(PrivatePage):
    def get_template_context(self):
        context = super(PacientsPage, self).get_template_context()

        pacients = Pacient.query().fetch(20)

        context['pacients'] = pacients

        return context

    def get_page_template(self):
        return 'pacients.html'
        
    def post(self):
        context = super(PacientsPage, self).get_template_context()
        
        first_name = self.request.get("first_name")
        card_no = self.request.get("card_no")
        
        query = Pacient.query()
        
        if first_name:
            query = query.filter(Pacient.first_name == first_name )
            context['first_name'] = first_name
            
        if card_no:
            query = query.filter(Pacient.card_no == card_no )
            context['card_no'] = card_no
            
        pacients = query.fetch(20)
        
        context['pacients'] = pacients
        
        template = jinja_environment.get_template(self.get_page_template())
        self.response.out.write(template.render(context))

class CabinetPage(PrivatePage):
    pass

class PacientCreate(PrivatePage):
    def get_page_template(self):
        return 'pacient_card.html'
        
    def post(self):
        if not self.get_logged_user():
            self.abort(403)

        first_name = self.request.get("first_name")
        last_name = self.request.get("last_name")
        middle_name = self.request.get("middle_name")
        birthday_date = self.request.get("birthday_date")
        sex = self.request.get("sex")
        extra_data = self.request.get("extra_data")
        
        card_no = self.request.get("card_no")
        cycle_faze = self.request.get("cycle_faze")

        if first_name == "" or last_name == "" or birthday_date =="":
            return self.redirect('/pacients', body={"first_name": "bad_name"})

        pacient = Pacient()
        pacient.first_name = first_name
        pacient.last_name = last_name
        pacient.middle_name = middle_name
        pacient.birthday_date = datetime.datetime.strptime(birthday_date, "%d.%m.%Y")
        pacient.sex = sex
        pacient.card_no = card_no
        pacient.cycle_faze = cycle_faze

        pacient_key = pacient.put()
        
        self.redirect('/pacient/%d' % pacient_key.id())

class SaveAnalyzePage(BaseAuthHandler):
    def post(self):
        if not self.get_logged_user():
            self.abort(403)

        analyze_type = self.request.get("analyze_type")
        analyze_value = self.request.get("analyze_value")
        pacient_id = self.request.get("pacient_id")
        pacient_key = ndb.Key(Pacient, int(pacient_id)) 
        
        print(self.request.POST)

        pacient_analyze = PacientAnalyze.query(PacientAnalyze.pacient_key == pacient_key, PacientAnalyze.analyze_type == analyze_type).get()
        if not pacient_analyze:
            pacient_analyze = PacientAnalyze(analyze_type=analyze_type, analyze_value=analyze_value, pacient_key=pacient_key)

        pacient_analyze.analyze_value = analyze_value

        print(pacient_analyze)
        pacient_analyze.put(use_cache=False)
        future = pacient_analyze.put_async()

        future.get_result()
        
        self.redirect('/pacient/%d' % pacient_key.id())

class RemoveAnalyzePage(BaseAuthHandler):
    @ndb.toplevel
    def get(self, pacient_id, analyze_type):
        if not self.get_logged_user():
            self.abort(403)

        pacient_key = ndb.Key(Pacient, int(pacient_id)) 

        pacient_analyze = PacientAnalyze.query(PacientAnalyze.pacient_key == pacient_key, PacientAnalyze.analyze_type == analyze_type).get()
        if pacient_analyze:
            result = pacient_analyze.key.delete_async().get_result()

        self.redirect('/pacient/%d' % pacient_key.id())

class PacientPage(AppPage):

    def get(self, pacient_id):
        if not self.get_logged_user():
            self.abort(403)

        context = self.get_template_context()
        pacient = Pacient.get_by_id(int(pacient_id))
        context['pacient'] = pacient

        analyzes = PacientAnalyze.query(PacientAnalyze.pacient_key == pacient.key).order(PacientAnalyze.date).fetch()
        context['analyzes'] = analyzes

        template = jinja_environment.get_template(self.analyze(pacient, analyzes))

        self.response.out.write(template.render(context))

    def get_page_template(self):
        return 'pacient_info.html'

    def analyze(self, pacient, analyzes):

        analyze_value_map = {}
        for analyze in analyzes:
            analyze_value_map[analyze.analyze_type] = analyze.analyze_value
            
        user_analyzes = UserAnalyzes(pacient, analyze_value_map)

        mcv_cmp = user_analyzes.compare_value('MCV')
        if not mcv_cmp.is_present():
            return mcv_cmp.get_template() 
        
        # if not 'MCH' in analyze_value_map:
            # return 'forms/analyze/mch.html'

        if mcv_cmp.is_lower():
            is_left_branch = False
            
            fe_cmp = user_analyzes.compare_value('Fe')
            ferritin_cmp = user_analyzes.compare_value('Ferritin')
            
            if not fe_cmp.is_present():
                return fe_cmp.get_template() 
            
            # if not ferritin_cmp.is_present():
            #     return ferritin_cmp.get_template()
            
            if fe_cmp.is_norm():
                if not 'Ferritin' in analyze_value_map:
                    return 'forms/analyze/ferritin.html'

                Ferritin = analyze_value_map['Ferritin']
                if Ferritin == VALUE_DOWN:
                    is_left_branch = True

            elif fe_cmp.is_lower():
                is_left_branch = True

            if is_left_branch:
                return 'forms/result/zhda.html'

            coe_cmp = user_analyzes.compare_value('COE')
            srb_cmp = user_analyzes.compare_value('SRB')
            
            if coe_cmp.is_present():
                coe_srb_cmp = coe_cmp
            else: 
                coe_srb_cmp = srb_cmp
                
            if not coe_srb_cmp.is_present():
                return 'forms/analyze/coe_srb.html'

            if coe_srb_cmp.is_lower() or coe_srb_cmp.is_lower():
                return 'forms/result/unknown.html'
                
            if coe_srb_cmp.is_upper():
                return 'forms/result/ahz.html'
                
            if not 'FractG' in analyze_value_map:
                return 'forms/analyze/fract_gemoglob.html'

            FractG = analyzes_map['FractG'].get_value(analyze_value_map['FractG'])
            
            try:
                fg_a = float(FractG[u'a'])
            except ValueError:
                fg_a = 0
                
            try:
                fg_a2 = float(FractG[u'a2'])
            except ValueError:
                fg_a2 = 0
                
            try:
                fg_f = float(FractG[u'f'])
            except ValueError:
                fg_f = 0
                
            try:
                fg_s = float(FractG[u's'])
            except ValueError:
                fg_s = 0
                
            fg_anom = FractG[u'anom']
            
            if fg_a > 97 and fg_a2 < 3 and fg_f < 1:
                return 'forms/result/ahz_2.html'
                
            if fg_a2 > 3 or fg_f > 1:
                return 'forms/result/beta_talassem.html'
                
            if fg_s > 0:
                return 'forms/result/gemoglobinopaty_s.html'
                
            if fg_a < 97 and fg_anom:
                return 'forms/result/gemoglobinopaty_other.html'

            return 'forms/result/unknown.html'

        if mcv_cmp.is_upper():
            
        # right tree start #
        
            b12_cmp = user_analyzes.compare_value('B12')
            if not b12_cmp.is_present():
                return b12_cmp.get_template() 
                
            if b12_cmp.is_lower():
                return 'forms/result/b12deficit.html'
        
            folats_cmp = user_analyzes.compare_value('Folats')
            if not folats_cmp.is_present():
                return folats_cmp.get_template() 

            if folats_cmp.is_lower():
                return 'forms/result/folideficit.html'

            if b12_cmp.is_norm() and folats_cmp.is_norm():
                ret_cmp = user_analyzes.compare_value('Ret')
                if not ret_cmp.is_present():
                    return ret_cmp.get_template() 
                
                if ret_cmp.is_upper():
                    return 'forms/result/gemolitich_anemia.html'
    
                else:
                    srb_cmp = user_analyzes.compare_value('SRB')
                    if not srb_cmp.is_present():
                        return srb_cmp.get_template() 
                    
                    if srb_cmp.is_norm():
                        return 'forms/result/postgemor_anemia.html'
                    else:
                        return 'forms/result/ahz.html'
            
        # right tree end #

        # central tree start #
        
        if mcv_cmp.is_norm():
        
            ret_cmp = user_analyzes.compare_value('Ret')
            if not ret_cmp.is_present():
                return ret_cmp.get_template() 
    
            if ret_cmp.is_upper():
                return 'forms/result/gemolitich_anemia.html'
    
                # if not 'NBiliruby' in analyze_value_map:
                #     return 'forms/analyze/nbiliruby.html'
    
                # NBiliruby = analyze_value_map['NBiliruby']
                
                # if NBiliruby == VALUE_UP:
                #     return 'forms/result/gemolitich_anemia.html'
    
                # if NBiliruby == VALUE_N:
                #     return 'forms/result/orragich_anemia.html'
    
                # return 'forms/result/unknown.html'
    
            fe_cmp = user_analyzes.compare_value('Fe')
            ferritin_cmp = user_analyzes.compare_value('Ferritin')
            
            if not fe_cmp.is_present():
                return fe_cmp.get_template() 
            
            if not ferritin_cmp.is_present():
                return ferritin_cmp.get_template() 
                
            if (fe_cmp.is_lower() or fe_cmp.is_norm()) and ferritin_cmp.is_lower():
                return 'forms/result/zhda.html'
                
            if fe_cmp.is_norm() and (ferritin_cmp.is_norm() or ferritin_cmp.is_upper()):
                rbc_cmp = user_analyzes.compare_value('RBC')
                wbc_cmp = user_analyzes.compare_value('WBC')
                plt_cmp = user_analyzes.compare_value('PLT')
                
                if not rbc_cmp.is_present():
                    return rbc_cmp.get_template() 
                    
                if not wbc_cmp.is_present():
                    return wbc_cmp.get_template() 
                    
                if not plt_cmp.is_present():
                    return plt_cmp.get_template() 
                    
                if rbc_cmp.is_lower() and wbc_cmp.is_lower() and plt_cmp.is_lower():
                    return 'forms/result/aplastich_anemia.html'
                else:
                    srb_cmp = user_analyzes.compare_value('SRB')
                    if not srb_cmp.is_present():
                        return srb_cmp.get_template() 
                    
                    if srb_cmp.is_norm():
                        return 'forms/result/postgemor_anemia.html'
                    else:
                        return 'forms/result/ahz.html'
                        
        # central tree end #

        # if not 'COE' in analyze_value_map:
        #     return 'forms/analyze/coe.html'

        # COE = analyze_value_map['COE']

        # if COE == VALUE_UP:
        #     return 'forms/result/ahz.html'

        # if not 'RBC' in analyze_value_map:
        #     return 'forms/analyze/rbc.html'

        # RBC = analyze_value_map['RBC']

        # if RBC == VALUE_DOWN:
        #     return 'forms/result/aplastich_anemia.html'

        return 'forms/result/unknown.html'

application = ndb.toplevel(webapp2.WSGIApplication([
    ('/', HomePage),
    ('/pacients', PacientsPage),
    ('/stats', AppPage),
    ('/cabinet', AppPage),
    ('/pacient-create', PacientCreate),
    ('/pacient/(\d+)', PacientPage),
    ('/save-analyze', SaveAnalyzePage),
    ('/remove-analyze/(\d+)/(\w+)', RemoveAnalyzePage),
], debug=True))
