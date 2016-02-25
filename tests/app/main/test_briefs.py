# coding: utf-8
from __future__ import unicode_literals

import mock
from dmapiclient import api_stubs, HTTPError
from dmutils.email import MandrillException
from nose.tools import assert_equal, assert_in
from ..helpers import BaseApplicationTest, FakeMail
from lxml import html


brief_form_submission = {
    "availability": "Next Tuesday",
    "dayRate": "£200",
    "essentialRequirements-0": True,
    "essentialRequirements-1": False,
    "essentialRequirements-2": True,
    "niceToHaveRequirements-0": False,
    "niceToHaveRequirements-1": True,
    "niceToHaveRequirements-2": False,
    "specialistName": "Dave",
}

processed_brief_submission = {
    "availability": "Next Tuesday",
    "dayRate": "£200",
    "essentialRequirements": [
        True,
        False,
        True
    ],
    "niceToHaveRequirements": [
        False,
        True,
        False
    ],
    "specialistName": "Dave",
}


@mock.patch('app.main.views.briefs.data_api_client', autospec=True)
class TestBriefClarificationQuestions(BaseApplicationTest):
    def test_clarification_question_form_requires_login(self, data_api_client):
        res = self.client.get('/suppliers/opportunities/1/ask-a-question')
        assert res.status_code == 302
        assert '/login' in res.headers['Location']

    def test_clarification_question_form(self, data_api_client):
        self.login()
        data_api_client.get_brief.return_value = {'briefs': {'status': 'live'}}

        res = self.client.get('/suppliers/opportunities/1/ask-a-question')
        assert res.status_code == 200

    def test_clarification_question_form_requires_existing_brief_id(self, data_api_client):
        self.login()
        data_api_client.get_brief.side_effect = HTTPError(mock.Mock(status_code=404))

        res = self.client.get('/suppliers/opportunities/1/ask-a-question')
        assert res.status_code == 404

    def test_clarification_question_form_requires_live_brief(self, data_api_client):
        self.login()
        data_api_client.get_brief.return_value = {'briefs': {'status': 'expired'}}

        res = self.client.get('/suppliers/opportunities/1/ask-a-question')
        assert res.status_code == 404


@mock.patch('app.main.views.briefs.data_api_client', autospec=True)
class TestSubmitClarificationQuestions(BaseApplicationTest):
    def test_submit_clarification_question_requires_login(self, data_api_client):
        res = self.client.post('/suppliers/opportunities/1/ask-a-question')
        assert res.status_code == 302
        assert '/login' in res.headers['Location']

    @mock.patch('app.main.helpers.briefs.send_email')
    def test_submit_clarification_question(self, send_email, data_api_client):
        self.login()
        data_api_client.get_brief.return_value = api_stubs.brief(status="live")
        data_api_client.get_brief.return_value['briefs']['frameworkName'] = 'Brief Framework Name'

        res = self.client.post('/suppliers/opportunities/1234/ask-a-question', data={
            'clarification-question': "important question",
        })
        assert res.status_code == 200

        send_email.assert_has_calls([
            mock.call(
                from_name='Brief Framework Name Supplier',
                tags=['brief-clarification-question'],
                email_body=FakeMail("important question"),
                from_email='do-not-reply@digitalmarketplace.service.gov.uk',
                api_key='MANDRILL',
                to_email_addresses=['buyer@email.com'],
                subject=u"You\u2019ve received a new supplier question about \u2018I need a thing to do a thing\u2019"
            ),
            mock.call(
                from_name='Digital Marketplace Admin',
                tags=['brief-clarification-question-confirmation'],
                email_body=FakeMail("important question"),
                from_email='do-not-reply@digitalmarketplace.service.gov.uk',
                api_key='MANDRILL',
                to_email_addresses=['email@email.com'],
                subject=u"Your question about \u2018I need a thing to do a thing\u2019"
            ),
        ])

    @mock.patch('app.main.helpers.briefs.send_email')
    def test_submit_clarification_question_fails_on_mandrill_error(self, send_email, data_api_client):
        self.login()
        data_api_client.get_brief.return_value = api_stubs.brief(status="live")
        data_api_client.get_brief.return_value['briefs']['frameworkName'] = 'Framework Name'

        send_email.side_effect = MandrillException

        res = self.client.post('/suppliers/opportunities/1234/ask-a-question', data={
            'clarification-question': "important question",
        })
        assert res.status_code == 503

    def test_submit_clarification_question_requires_existing_brief_id(self, data_api_client):
        self.login()
        data_api_client.get_brief.side_effect = HTTPError(mock.Mock(status_code=404))

        res = self.client.post('/suppliers/opportunities/1/ask-a-question')
        assert res.status_code == 404

    def test_submit_clarification_question_requires_live_brief(self, data_api_client):
        self.login()
        data_api_client.get_brief.return_value = {'briefs': {'status': 'expired'}}

        res = self.client.post('/suppliers/opportunities/1/ask-a-question')
        assert res.status_code == 404

    def test_submit_empty_clarification_question_returns_validation_error(self, data_api_client):
        self.login()
        data_api_client.get_brief.return_value = {'briefs': {'status': 'live'}}

        res = self.client.post('/suppliers/opportunities/1/ask-a-question', data={
            'clarification-question': "",
        })
        assert res.status_code == 400
        assert "cannot be empty" in res.get_data(as_text=True)

    def test_submit_empty_clarification_question_has_max_length_limit(self, data_api_client):
        self.login()
        data_api_client.get_brief.return_value = {'briefs': {'status': 'live'}}

        res = self.client.post('/suppliers/opportunities/1/ask-a-question', data={
            'clarification-question': "a" * 5100,
        })
        assert res.status_code == 400
        assert "cannot be longer than" in res.get_data(as_text=True)


@mock.patch("app.main.views.briefs.data_api_client")
class TestRespondToBrief(BaseApplicationTest):

    def setup(self):
        super(TestRespondToBrief, self).setup()

        self.brief = api_stubs.brief(status='live')
        self.brief['briefs']['essentialRequirements'] = ['Essential one', 'Essential two', 'Essential three']
        self.brief['briefs']['niceToHaveRequirements'] = ['Nice one', 'Top one', 'Get sorted']

        lots = [api_stubs.lot(slug="digital-specialists", allows_brief=True)]
        self.framework = api_stubs.framework(status="live", slug="digital-outcomes-and-specialists",
                                             clarification_questions_open=False, lots=lots)

        with self.app.test_client():
            self.login()

    def test_get_submit_brief_response_page(self, data_api_client):
        data_api_client.get_brief.return_value = self.brief
        data_api_client.get_framework.return_value = self.framework
        res = self.client.get('/suppliers/opportunities/1234/responses/create')
        doc = html.fromstring(res.get_data(as_text=True))

        assert_equal(res.status_code, 200)
        data_api_client.get_brief.assert_called_once_with(1234)
        assert_equal(
            len(doc.xpath('//h1[contains(text(), "Apply to an opportunity")]')), 1)
        assert_equal(
            len(doc.xpath('//h2[contains(text(), "Do you fulfill the following essential requirements")]')), 1)
        assert_equal(
            len(doc.xpath('//h2[contains(text(), "Do you fulfill the following nice-to-have requirements?")]')), 1)

    def test_get_submit_brief_response_page_404_for_not_live_brief(self, data_api_client):
        brief = self.brief.copy()
        brief['briefs']['status'] = 'draft'
        data_api_client.get_brief.return_value = brief
        data_api_client.get_framework.return_value = self.framework
        res = self.client.get('/suppliers/opportunities/1234/responses/create')

        assert_equal(res.status_code, 404)

    def test_get_submit_brief_response_page_404_for_not_live_framework(self, data_api_client):
        framework = self.framework.copy()
        framework['frameworks']['status'] = 'standstill'
        data_api_client.get_brief.return_value = self.brief
        data_api_client.get_framework.return_value = framework
        res = self.client.get('/suppliers/opportunities/1234/responses/create')

        assert_equal(res.status_code, 404)

    def test_get_submit_brief_response_page_includes_essential_requirements(self, data_api_client):
        data_api_client.get_brief.return_value = self.brief
        data_api_client.get_framework.return_value = self.framework
        res = self.client.get('/suppliers/opportunities/1234/responses/create')
        doc = html.fromstring(res.get_data(as_text=True))

        assert_equal(
            len(doc.xpath('//p[contains(text(), "Essential one")]')), 1)
        assert_equal(
            len(doc.xpath('//p[contains(text(), "Essential two")]')), 1)
        assert_equal(
            len(doc.xpath('//p[contains(text(), "Essential three")]')), 1)

    def test_get_submit_brief_response_page_includes_nice_to_have_requirements(self, data_api_client):
        data_api_client.get_brief.return_value = self.brief
        data_api_client.get_framework.return_value = self.framework
        res = self.client.get('/suppliers/opportunities/1234/responses/create')
        doc = html.fromstring(res.get_data(as_text=True))

        assert_equal(
            len(doc.xpath('//p[contains(text(), "Top one")]')), 1)
        assert_equal(
            len(doc.xpath('//p[contains(text(), "Nice one")]')), 1)
        assert_equal(
            len(doc.xpath('//p[contains(text(), "Get sorted")]')), 1)

    def test_get_submit_brief_response_page_redirects_to_login_for_buyer(self, data_api_client):
        data_api_client.get_brief.return_value = self.brief
        data_api_client.get_framework.return_value = self.framework
        self.login_as_buyer()
        res = self.client.get('/suppliers/opportunities/1234/responses/create')

        assert_equal(res.status_code, 302)
        assert_equal(res.location,
                     "http://localhost/login?next=%2Fsuppliers%2Fopportunities%2F1234%2Fresponses%2Fcreate")
        self.assert_flashes("supplier-role-required", "error")

    def test_post_create_new_brief_response(self, data_api_client):
        data_api_client.get_brief.return_value = self.brief
        data_api_client.get_framework.return_value = self.framework

        res = self.client.post(
            '/suppliers/opportunities/1234/responses/create',
            data=brief_form_submission
        )
        assert_equal(res.status_code, 302)
        assert_equal(res.location, "http://localhost/suppliers")
        self.assert_flashes("Your response to &lsquo;I need a thing to do a thing&rsquo; has been submitted.")
        data_api_client.create_brief_response.assert_called_once_with(1234, 1234, processed_brief_submission,
                                                                      'email@email.com')

    def test_post_create_new_brief_response_404_if_not_live_brief(self, data_api_client):
        brief = self.brief.copy()
        brief['briefs']['status'] = 'draft'
        data_api_client.get_brief.return_value = brief
        data_api_client.get_framework.return_value = self.framework

        res = self.client.post(
            '/suppliers/opportunities/1234/responses/create',
            data=brief_form_submission
        )
        assert_equal(res.status_code, 404)
        assert not data_api_client.create_brief_response.called

    def test_post_create_new_brief_response_404_if_not_live_framework(self, data_api_client):
        framework = self.framework.copy()
        framework['frameworks']['status'] = 'standstill'
        data_api_client.get_brief.return_value = self.brief
        data_api_client.get_framework.return_value = framework

        res = self.client.post(
            '/suppliers/opportunities/1234/responses/create',
            data=brief_form_submission
        )
        assert_equal(res.status_code, 404)
        assert not data_api_client.create_brief_response.called

    def test_post_create_new_brief_response_with_api_error_fails(self, data_api_client):
        data_api_client.get_brief.return_value = self.brief
        data_api_client.get_framework.return_value = self.framework
        data_api_client.create_brief_response.side_effect = HTTPError(
            mock.Mock(status_code=400),
            {'availability': 'answer_required'}
        )

        res = self.client.post(
            '/suppliers/opportunities/1234/responses/create',
            data=brief_form_submission
        )

        assert_equal(res.status_code, 400)
        assert_in("You need to answer this question.", res.get_data(as_text=True))
        data_api_client.create_brief_response.assert_called_once_with(1234, 1234, processed_brief_submission,
                                                                      'email@email.com')

    def test_post_create_new_brief_response_redirects_to_login_for_buyer(self, data_api_client):
        data_api_client.get_brief.return_value = self.brief
        data_api_client.get_framework.return_value = self.framework
        self.login_as_buyer()
        res = self.client.post(
            '/suppliers/opportunities/1234/responses/create',
            data=brief_form_submission
        )
        assert_equal(res.status_code, 302)
        assert_equal(res.location, "http://localhost/login")
        self.assert_flashes("supplier-role-required", "error")
        assert not data_api_client.get_brief.called
