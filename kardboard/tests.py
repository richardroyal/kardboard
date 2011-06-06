import datetime
import random

import unittest2


class KardboardTestCase(unittest2.TestCase):
    def setUp(self):
        import kardboard
        from flaskext.mongoengine import MongoEngine

        kardboard.app.config['MONGODB_DB'] = 'kardboard-unittest'
        kardboard.app.config.from_object('kardboard.default_settings')
        kardboard.app.db = MongoEngine(kardboard.app)

        self._flush_db()

        self.app = kardboard.app.test_client()

        self.used_keys = []
        super(KardboardTestCase, self).setUp()

    def _flush_db(self):
        from mongoengine.connection import _get_db
        db = _get_db()
        #Truncate/wipe the test database
        names = [name for name in db.collection_names() \
            if 'system.' not in name]
        [db.drop_collection(name) for name in names]

    def _get_target_url(self):
        raise NotImplementedError

    def _get_target_class(self):
        raise NotImplementedError

    def _make_one(self, *args, **kwargs):
        return self._get_target_class()(*args, **kwargs)

    def _get_card_class(self):
        from kardboard.models import Kard
        return Kard

    def _get_board_class(self):
        from kardboard.models import Board
        return Board

    def _make_unique_key(self):
        key = random.randint(1, 10000)
        if key not in self.used_keys:
            self.used_keys.append(key)
            return key
        return self._make_unique_key()

    def make_card(self, **kwargs):
        key = self._make_unique_key()
        fields = {
            'key': "CMSAD-%s" % key,
            'title': "There's always money in the banana stand",
            'backlog_date': datetime.datetime.now()
        }
        fields.update(**kwargs)
        k = self._get_card_class()(**fields)
        return k

    def make_board(self, **kwargs):
        key = self._make_unique_key()
        fields = {
            'name': "Teamocil Board %s" % (key, ),
            'categories':
                ["Numbness", "Short-term memory loss", "Reduced sex-drive"],
        }
        fields.update(**kwargs)
        b = self._get_board_class()(**fields)
        return b


class UtilTests(unittest2.TestCase):
    def test_business_days(self):
        from kardboard.util import business_days_between

        wednesday = datetime.datetime(year=2011, month=6, day=1)
        next_wednesday = datetime.datetime(year=2011, month=6, day=8)
        result = business_days_between(wednesday, next_wednesday)
        self.assertEqual(result, 5)

        aday = datetime.datetime(year=2011, month=6, day=1)
        manydayslater = datetime.datetime(year=2012, month=6, day=1)
        result = business_days_between(aday, manydayslater)
        self.assertEqual(result, 262)

    def test_month_range(self):
        from kardboard.util import month_range

        today = datetime.datetime(year=2011, month=6, day=12)
        start, end = month_range(today)
        self.assertEqual(6, start.month)
        self.assertEqual(1, start.day)
        self.assertEqual(2011, start.year)

        self.assertEqual(6, end.month)
        self.assertEqual(30, end.day)
        self.assertEqual(2011, end.year)

    def test_week_range(self):
        from kardboard.util import week_range
        today = datetime.datetime(year=2011, month=5, day=12)
        start, end = week_range(today)

        self.assertEqual(5, start.month)
        self.assertEqual(8, start.day)
        self.assertEqual(2011, start.year)

        self.assertEqual(5, end.month)
        self.assertEqual(14, end.day)
        self.assertEqual(2011, end.year)

        today = datetime.datetime(year=2011, month=6, day=5)
        start, end = week_range(today)
        self.assertEqual(6, start.month)
        self.assertEqual(5, start.day)
        self.assertEqual(2011, start.year)

        self.assertEqual(6, end.month)
        self.assertEqual(11, end.day)
        self.assertEqual(2011, end.year)


class BoardTests(KardboardTestCase):
    def _get_target_class(self):
        return self._get_board_class()

    def _make_one(self, **kwargs):
        return self.make_board(**kwargs)

    def test_valid_board(self):
        b = self._make_one()
        b.save()
        self.assert_(b.id)

    def test_board_slug(self):
        b = self._make_one(name="Operation Hot Mother")
        b.save()
        expected = u"operation-hot-mother"
        self.assertEqual(expected, b.slug)


class KardTests(KardboardTestCase):
    def setUp(self):
        super(KardTests, self).setUp()
        self.done_card = self._make_one()
        self.done_card.backlog_date = datetime.datetime(
            year=2011, month=5, day=2)
        self.done_card.start_date = datetime.datetime(
            year=2011, month=5, day=9)
        self.done_card.done_date = datetime.datetime(
            year=2011, month=6, day=12)
        self.done_card.save()

        self.done_card2 = self._make_one()
        self.done_card2.backlog_date = datetime.datetime(
            year=2011, month=5, day=2)
        self.done_card2.start_date = datetime.datetime(
            year=2011, month=5, day=9)
        self.done_card2.done_date = datetime.datetime(
            year=2011, month=5, day=15)
        self.done_card2.save()

        self.wip_card = self._make_one(key="CMSLUCILLE-2")
        self.wip_card.backlog_date = datetime.datetime(
            year=2011, month=5, day=2)
        self.wip_card.start_date = datetime.datetime(
            year=2011, month=5, day=9)
        self.wip_card.save()

        self.elabo_card = self._make_one(key="GOB-1")
        self.elabo_card.backlog_date = datetime.datetime(
            year=2011, month=5, day=2)
        self.elabo_card.save()

    def _get_target_class(self):
        return self._get_card_class()

    def _make_one(self, **kwargs):
        return self.make_card(**kwargs)

    def test_valid_card(self):
        k = self._make_one()
        k.save()
        self.assert_(k.id)

    def test_done_cycle_time(self):
        self.assertEquals(25, self.done_card.cycle_time)
        self.assertEquals(25, self.done_card._cycle_time)

    def test_done_lead_time(self):
        self.assertEquals(30, self.done_card.lead_time)
        self.assertEquals(30, self.done_card._lead_time)

    def test_wip_cycle_time(self):
        today = datetime.datetime(year=2011, month=6, day=12)

        self.assertEquals(None, self.wip_card.cycle_time)
        self.assertEquals(None, self.wip_card._cycle_time)

        self.assertEquals(None, self.wip_card.lead_time)
        self.assertEquals(None, self.wip_card._lead_time)

        actual = self.wip_card.current_cycle_time(
                today=today)
        self.assertEquals(25, actual)

    def test_elabo_cycle_time(self):
        today = datetime.datetime(year=2011, month=6, day=12)

        self.assertEquals(None, self.elabo_card.cycle_time)
        self.assertEquals(None, self.elabo_card._cycle_time)

        self.assertEquals(None, self.elabo_card.lead_time)
        self.assertEquals(None, self.elabo_card._lead_time)

        actual = self.elabo_card.current_cycle_time(
                today=today)
        self.assertEquals(None, actual)

    def test_in_progress_manager(self):
        klass = self._get_target_class()
        now = datetime.datetime(2011, 6, 12)
        self.assertEqual(2, klass.in_progress(now).count())

    def test_completed_in_month(self):
        klass = self._get_target_class()
        self.assertEqual(1,
            klass.objects.done_in_month(year=2011, month=6).count())

    def test_moving_cycle_time(self):
        klass = self._get_target_class()
        expected = klass.objects.done().average('_cycle_time')

        expected = int(round(expected))
        actual = klass.objects.moving_cycle_time(
            year=2011, month=6, day=12)
        self.assertEqual(expected, actual)

    def test_done_in_week(self):
        klass = self._get_target_class()
        expected = 1
        actual = klass.objects.done_in_week(
            year=2011, month=6, day=15)

        self.assertEqual(expected, actual.count())


class KardTimeMachineTests(KardboardTestCase):
    def setUp(self):
        super(KardTimeMachineTests, self).setUp()
        self._set_up_data()

    def _get_target_class(self):
        return self._get_card_class()

    def _make_one(self, **kwargs):
        return self.make_card(**kwargs)

    def _set_up_data(self):
        klass = self._get_target_class()

        # Simulate creating 5 cards and moving
        # some forward
        backlog_date = datetime.datetime(
            year=2011, month=5, day=30)
        for i in xrange(0, 5):
            c = self._make_one(backlog_date=backlog_date)
            c.save()

        cards = klass.objects.all()[:2]
        for c in cards:
            c.start_date = backlog_date.replace(day=31)
            c.save()

        for c in cards:
            c.done_date = backlog_date.replace(month=6, day=2)
            c.save()

    def test_time_machine(self):
        klass = self._get_target_class()

        backlogged_day = datetime.datetime(
            year=2011, month=5, day=30)
        started_2_day = datetime.datetime(
            year=2011, month=5, day=31)
        finished_2_day = datetime.datetime(
            year=2011, month=6, day=2)

        today = datetime.datetime(
            year=2011, month=6, day=12)

        expected = 3
        actual = klass.in_progress(today)
        self.assertEqual(expected, actual.count())

        expected = 5
        actual = klass.in_progress(backlogged_day)
        self.assertEqual(expected, actual.count())

        expected = 5
        actual = klass.in_progress(started_2_day)
        self.assertEqual(expected, actual.count())

        expected = 3
        actual = klass.in_progress(finished_2_day)
        self.assertEqual(expected, actual.count())


class DashboardTestCase(KardboardTestCase):
    def setUp(self):
        super(DashboardTestCase, self).setUp()

        from kardboard.models import Kard
        self.Kard = Kard
        self.year = 2011
        self.month = 6
        self.day = 15

        self.board = self.make_board()
        self.board1 = self.make_board()

        for i in xrange(0, 5):
            #board will have 5 cards in elabo, started, and done
            k = self.make_card()  # elabo
            k.save()
            self.board.cards.append(k)

            k = self.make_card(start_date=datetime.datetime(
                year=self.year, month=self.month, day=12))
            k.save()
            self.board.cards.append(k)

            k = self.make_card(
                start_date=datetime.datetime(year=self.year,
                    month=self.month, day=12),
                done_date=datetime.datetime(year=self.year,
                    month=self.month, day=19))
            k.save()
            self.board.cards.append(k)

            self.board.save()

        for i in xrange(0, 3):
            #board will have 3 cards in elabo, started, and done
            k = self.make_card()  # backlogged
            k.save()
            self.board1.cards.append(k)

            k = self.make_card(start_date=datetime.datetime(
                year=2011, month=6, day=12))
            k.save()
            self.board1.cards.append(k)

            k = self.make_card(
                start_date=datetime.datetime(year=2011, month=6, day=12),
                done_date=datetime.datetime(year=2011, month=6, day=19))
            k.save()
            self.board1.cards.append(k)

            self.board1.save()


class HomepageTests(DashboardTestCase):
    def _get_target_url(self):
        return '/'

    def test_wip(self):
        rv = self.app.get(self._get_target_url())
        self.assertEqual(200, rv.status_code)

        expected_cards = self.Kard.objects.all()
        expected_cards = [c for c in expected_cards if c.done_date == None]

        for c in expected_cards:
            self.assertIn(c.key, rv.data)


class MonthPageTests(DashboardTestCase):
    def _get_target_url(self):
        return '/%s/%s/' % (self.year, self.month)

    def test_wip(self):
        rv = self.app.get(self._get_target_url())
        self.assertEqual(200, rv.status_code)

        date = datetime.datetime(self.year, self.month, self.day)
        expected_cards = self.Kard.in_progress(date)

        for c in expected_cards:
            self.assertIn(c.key, rv.data)

        expected = """<p class="value">%s</p>""" % expected_cards.count()
        self.assertIn(expected, rv.data)

    def test_done_month_metric(self):
        rv = self.app.get(self._get_target_url())
        self.assertEqual(200, rv.status_code)

        done_month = self.Kard.objects.done_in_month(
            year=self.year, month=self.month)

        expected = """<p class="value">%s</p>""" % done_month.count()
        self.assertIn(expected, rv.data)

    def test_cycle_time_metric(self):
        rv = self.app.get(self._get_target_url())
        self.assertEqual(200, rv.status_code)

        cycle_time = self.Kard.objects.moving_cycle_time(
            year=self.year, month=self.month)

        expected = """<p class="value">%s</p>""" % cycle_time
        self.assertIn(expected, rv.data)


class DayPageTests(DashboardTestCase):
    def _get_target_url(self):
        return '/%s/%s/%s/' % (self.year, self.month, self.day)

    def test_done_in_week_metric(self):
        rv = self.app.get(self._get_target_url())
        self.assertEqual(200, rv.status_code)

        done = self.Kard.objects.done_in_week(
            year=self.year, month=self.month, day=self.day).count()

        expected = """<p class="value">%s</p>""" % done
        self.assertIn(expected, rv.data)


class DonePageTests(DashboardTestCase):
    def _get_target_url(self):
        return '/done/'

    def test_done_page(self):
        rv = self.app.get(self._get_target_url())
        self.assertEqual(200, rv.status_code)

        done = self.Kard.objects.done()

        for c in done:
            self.assertIn(c.key, rv.data)


class DoneReportTests(DashboardTestCase):
    def _get_target_url(self):
        return '/done/report/%s/%s/' % (self.year, self.month)

    def test_done_report(self):
        rv = self.app.get(self._get_target_url())
        self.assertEqual(200, rv.status_code)
        self.assertIn("text/plain", rv.headers['Content-Type'])

        done = self.Kard.objects.done_in_month(
            month=self.month, year=self.year)

        for c in done:
            self.assertIn(c.key, rv.data)


class FormTests(KardboardTestCase):
    pass


class CardFormTest(FormTests):
    def setUp(self):
        super(CardFormTest, self).setUp()
        self.form = self._make_one()
        self.required_data = {
            'key': u'CMSIF-199',
            'title': u'You gotta lock that down',
            'backlog_date': u"06/11/2011",
            'category': u'Bug',
        }

    def _get_target_class(self):
        from kardboard.forms import CardForm
        return CardForm

    def test_required_fields(self):
        self.form.process(**self.required_data)
        self.form.validate()
        self.assertEquals(0, len(self.form.errors))

        card = self._get_card_class()()
        self.form.populate_obj(card)
        card.save()

    def test_datetime_coercing(self):
        self.form.process(**self.required_data)
        data = self.form.backlog_date.data
        self.assertEqual(6, data.month)

    def test_key_uniqueness(self):
        klass = self._get_card_class()
        c = klass(**self.required_data)
        c.backlog_date = datetime.datetime.now()
        c.save()

        self.form.process(**self.required_data)
        self.form.validate()
        self.assertEquals(1, len(self.form.errors))
        self.assertIn('key', self.form.errors.keys())


class CRUDTests(KardboardTestCase):
    pass


class CardAddTests(CRUDTests):
    def setUp(self):
        super(CardAddTests, self).setUp()
        self.required_data = {
            'key': u'CMSIF-199',
            'title': u'You gotta lock that down',
            'backlog_date': u"06/11/2011",
            'category': u'Bug',
        }

    def _get_target_url(self):
        return '/card/add/'

    def _get_target_class(self):
        return self._get_card_class()

    def ztest_add_card(self):
        klass = self._get_target_class()

        res = self.app.get(self._get_target_url())
        self.assertEqual(200, res.status_code)
        self.assertIn('<form', res.data)

        res = self.app.post(self._get_target_url(),
            data=self.required_data)
        self.assertEqual(302, res.status_code)
        self.assertEqual(1, klass.objects.count())

        k = klass.objects.get(key=self.required_data['key'])
        self.assert_(k.id)


if __name__ == "__main__":
    unittest2.main()
