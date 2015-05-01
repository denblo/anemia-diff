# -*- coding: utf-8 -*-
import jinja2
import os
import webapp2
import datetime

from google.appengine.api import users
from google.appengine.ext import ndb

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
    first_name = ndb.StringProperty(indexed=False)
    last_name = ndb.StringProperty(indexed=False)
    middle_name = ndb.StringProperty(indexed=False)
    birthday_date = ndb.DateTimeProperty(auto_now_add=False)
    sex = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    extra = ndb.StringProperty(indexed=False)

class PacientAnalyze(ndb.Model):
    pacient_key = ndb.KeyProperty()
    #analyze_type = ndb.KeyProperty()
    analyze_type = ndb.StringProperty()
    analyze_value = ndb.StringProperty(indexed=False)

menu_items = [
        ("/cabinet",u'Личный кабинет' ),
        ("/pacients",u'Пациенты' ),
        ("/stats", u'Статистика'),
        ("/about", u'О программе')
        ]

anonymouse_menu_items = [
        ("/about", u'О программе')
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

class PacientsPage(PrivatePage):
    def get_template_context(self):
        context = super(PacientsPage, self).get_template_context()

        pacients = Pacient.query().fetch(20)

        context['pacients'] = pacients

        return context

    def get_page_template(self):
        return 'pacient_card.html'

class CabinetPage(PrivatePage):
    pass

class PacientCreate(BaseAuthHandler):
    def post(self):
        if not self.get_logged_user():
            self.abort(403)

        first_name = self.request.get("first_name")
        last_name = self.request.get("last_name")
        middle_name = self.request.get("middle_name")
        birthday_date = self.request.get("birthday_date")
        sex = self.request.get("sex")
        extra_data = self.request.get("extra_data")

        if first_name == "" or last_name == "" or birthday_date =="":
            return self.redirect('/pacients', body={"first_name": "bad_name"})

        pacient = Pacient()
        pacient.first_name = first_name
        pacient.last_name = last_name
        pacient.middle_name = middle_name
        pacient.birthday_date = datetime.datetime.strptime(birthday_date, "%d.%m.%Y")
        pacient.sex = sex

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

        pacient_analyze = PacientAnalyze.query(PacientAnalyze.pacient_key == pacient_key, PacientAnalyze.analyze_type == analyze_type).get()
        if not pacient_analyze:
            pacient_analyze = PacientAnalyze(analyze_type=analyze_type, analyze_value=analyze_value, pacient_key=pacient_key)

        pacient_analyze.analyze_value = analyze_value

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

        analyzes = PacientAnalyze.query(PacientAnalyze.pacient_key == pacient.key).fetch()
        context['analyzes'] = analyzes

        template = jinja_environment.get_template(self.analyze(pacient, analyzes))

        self.response.out.write(template.render(context))

    def get_page_template(self):
        return 'pacient_info.html'

    def analyze(self, pacient, analyzes):

        analyze_value_map = {}
        for analyze in analyzes:
            analyze_value_map[analyze.analyze_type] = analyze.analyze_value

        if not 'MCV' in analyze_value_map:
            return 'forms/analyze/mcv.html'

        if not 'MCH' in analyze_value_map:
            return 'forms/analyze/mch.html'

        MCV = int(analyze_value_map['MCV'])
        MCH = int(analyze_value_map['MCH'])

        if MCV < 80:
            is_left_branch = False

            if not 'Fe' in analyze_value_map:
                return 'forms/analyze/fe.html'

            Fe = analyze_value_map['Fe']
            if Fe == 'N':
                if not 'Ferritin' in analyze_value_map:
                    return 'forms/analyze/ferritin.html'

                Ferritin = analyze_value_map['Ferritin']
                if Ferritin == VALUE_DOWN:
                    is_left_branch = True

            elif Fe == VALUE_DOWN:
                is_left_branch = True

            if is_left_branch:
                return 'forms/result/zhda.html'

            if not 'COE' in analyze_value_map:
                return 'forms/analyze/coe.html'

            if not 'SRB' in analyze_value_map:
                return 'forms/analyze/srb.html'

            COE = analyze_value_map['COE']
            SRB = analyze_value_map['SRB']
            
            if COE == VALUE_DOWN or SRB == VALUE_DOWN:
                return 'forms/result/unknown.html'

            if not 'Hb' in analyze_value_map:
                return 'forms/analyze/hb.html'

            Hb = analyze_value_map['Hb']

            if Hb == VALUE_UP:
                return 'forms/result/gemoglobinopaty.html'

            if Hb == VALUE_N:
                return 'forms/result/ahz.html'

            return 'forms/result/unknown.html'

        if MCH > 100:
            if not 'Bfolats' in analyze_value_map:
                return 'forms/analyze/bfolats.html'

            Bfolats = analyze_value_map['Bfolats']

            if Bfolats == VALUE_DOWN:
                return 'forms/result/anemia_b_deficit.html'

            if not 'Ret' in analyze_value_map:
                return 'forms/analyze/ret.html'

            Ret = analyze_value_map['Ret']
            
            if Ret == VALUE_UP:
                return 'forms/result/gemolitich_anemia.html'

            return 'forms/result/ahz.html'

        if not 'Ret' in analyze_value_map:
            return 'forms/analyze/ret.html'

        Ret = analyze_value_map['Ret']

        if Ret == VALUE_UP:

            if not 'NBiliruby' in analyze_value_map:
                return 'forms/analyze/nbiliruby.html'

            NBiliruby = analyze_value_map['NBiliruby']
            
            if NBiliruby == VALUE_UP:
                return 'forms/result/gemolitich_anemia.html'

            if NBiliruby == VALUE_N:
                return 'forms/result/orragich_anemia.html'

            return 'forms/result/unknown.html'

        is_left_branch = False

        if not 'Fe' in analyze_value_map:
            return 'forms/analyze/fe.html'

        Fe = analyze_value_map['Fe']
        if Fe == 'N':
            if not 'Ferritin' in analyze_value_map:
                return 'forms/analyze/ferritin.html'

            Ferritin = analyze_value_map['Ferritin']
            if Ferritin == VALUE_DOWN:
                is_left_branch = True

        elif Fe == VALUE_DOWN:
            is_left_branch = True

        if is_left_branch:
            return 'forms/result/zhda.html'

        if not 'COE' in analyze_value_map:
            return 'forms/analyze/coe.html'

        COE = analyze_value_map['COE']

        if COE == VALUE_UP:
            return 'forms/result/ahz.html'

        if not 'RBC' in analyze_value_map:
            return 'forms/analyze/rbc.html'

        RBC = analyze_value_map['RBC']

        if RBC == VALUE_DOWN:
            return 'forms/result/aplastich_anemia.html'

        return 'forms/result/unknown.html'

application = ndb.toplevel(webapp2.WSGIApplication([
    ('/', AppPage),
    ('/pacients', PacientsPage),
    ('/stats', AppPage),
    ('/about', AppPage),
    ('/cabinet', AppPage),
    ('/pacient-create', PacientCreate),
    ('/pacient/(\d+)', PacientPage),
    ('/save-analyze', SaveAnalyzePage),
    ('/remove-analyze/(\d+)/(\w+)', RemoveAnalyzePage),
], debug=True))
