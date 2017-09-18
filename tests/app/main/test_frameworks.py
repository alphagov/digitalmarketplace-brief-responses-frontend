# -*- coding: utf-8 -*-
import mock
from lxml import html
from dmapiclient import APIError
from ..helpers import BaseApplicationTest


@mock.patch('app.main.views.frameworks.data_api_client', autospec=True)
class TestOpportunitiesDashboard(BaseApplicationTest):
    opportunities_dashboard_url = '/suppliers/opportunities/frameworks/digital-outcomes-and-specialists-2'

    def setup_method(self, method):
        super(TestOpportunitiesDashboard, self).setup_method(method)
        self.framework_response = {
            'frameworks': {
                'slug': 'digital-outcomes-and-specialists-2',
                'framework': 'digital-outcomes-and-specialists'
            }
        }
        self.supplier_framework_response = {
            'frameworkInterest': {'onFramework': True}
        }
        self.find_brief_responses_response = {'briefResponses': [
            {
                'briefId': 100,
                'brief': {
                    'title': 'Highest date, submitted, lowest id',
                    'applicationsClosedAt': '2017-06-08T10:26:21.538917Z',
                    'status': 'closed',
                    'frameworkSlug': 'digital-outcomes-and-specialists-2'
                },
                'status': 'submitted',
            },
            {
                'briefId': 1829,
                'brief': {
                    'title': 'Lowest date, submitted, mid id',
                    'applicationsClosedAt': '2017-06-06T10:26:21.538917Z',
                    'status': 'closed',
                    'frameworkSlug': 'digital-outcomes-and-specialists-2'
                },
                'status': 'submitted',
            },
            {
                'briefId': 4734,
                'brief': {
                    'title': 'Mid date, submitted, highest id',
                    'applicationsClosedAt': '2017-06-07T10:26:21.538917Z',
                    'status': 'withdrawn',
                    'frameworkSlug': 'digital-outcomes-and-specialists-2'
                },
                'status': 'submitted',
            }
        ]}

    def get_table_rows_by_id(self, table_id, data_api_client):
        """Helper function to get our 3 table rows as strings."""
        data_api_client.get_framework.return_value = self.framework_response
        data_api_client.get_supplier_framework_info.return_value = self.supplier_framework_response
        data_api_client.find_brief_responses.return_value = self.find_brief_responses_response
        with self.client:
            self.login()
            res = self.client.get(self.opportunities_dashboard_url)

            assert res.status_code == 200

            doc = html.fromstring(res.get_data(as_text=True))
            xpath_string = ".//*[@id='{}']/following-sibling::table[1]".format(table_id)
            table = doc.xpath(xpath_string)[0]
            rows = table.find_class('summary-item-row')
            return rows

    def test_request_works_and_correct_data_is_fetched(self, data_api_client):
        data_api_client.get_supplier_framework_info.return_value = self.supplier_framework_response
        data_api_client.get_framework.return_value = self.framework_response
        with self.client:
            self.login()
            resp = self.client.get(self.opportunities_dashboard_url)
            assert resp.status_code == 200
            data_api_client.find_brief_responses.assert_called_once_with(
                supplier_id=1234,
                framework='digital-outcomes-and-specialists-2'
            )

    def test_404_if_framework_does_not_exist(self, data_api_client):
        data_api_client.get_framework.side_effect = APIError(mock.Mock(status_code=404))
        with self.client:
            self.login()
            resp = self.client.get('/suppliers/frameworks/does-not-exist/opportunities')

            assert resp.status_code == 404

    def test_404_if_supplier_framework_does_not_exist(self, data_api_client):
        data_api_client.get_framework.return_value = self.framework_response
        data_api_client.get_supplier_framework_info.side_effect = APIError(mock.Mock(status_code=404))
        with self.client:
            self.login()
            resp = self.client.get(self.opportunities_dashboard_url)

            assert resp.status_code == 404

    def test_404_if_framework_is_not_dos(self, data_api_client):
        self.framework_response['frameworks'].update({'slug': 'g-cloud-9', 'framework': 'g-cloud'})
        data_api_client.get_framework.return_value = self.framework_response
        data_api_client.get_supplier_framework_info.return_value = self.supplier_framework_response
        with self.client:
            self.login()
            resp = self.client.get('/suppliers/frameworks/g-cloud-9/opportunities')

            assert resp.status_code == 404

    def test_404_if_supplier_not_on_framework(self, data_api_client):
        data_api_client.get_framework.return_value = self.framework_response
        self.supplier_framework_response['frameworkInterest'].update(
            {'onFramework': False}
        )
        data_api_client.get_supplier_framework_info.return_value = self.supplier_framework_response
        with self.client:
            self.login()
            resp = self.client.get(self.opportunities_dashboard_url)

            assert resp.status_code == 404

    def test_completed_list_of_opportunities(self, data_api_client):
        """Assert the 'Completed opportunities' table on this page contains the correct values."""
        first_row, second_row, third_row = self.get_table_rows_by_id('submitted-opportunities', data_api_client)

        assert 'Highest date, submitted, lowest id' in first_row.text_content()
        assert first_row.xpath('*//a/@href')[0] == '/suppliers/opportunities/100/responses/result'
        assert 'Thursday 8 June 2017' in first_row.text_content()

    def test_completed_list_of_opportunities_ordered_by_applications_closed_at(self, data_api_client):
        """Assert the 'Completed opportunities' table on this page contains the brief responses in the correct order."""
        first_row, second_row, third_row = self.get_table_rows_by_id('submitted-opportunities', data_api_client)

        assert 'Highest date' in first_row.text_content()
        assert 'Mid date' in second_row.text_content()
        assert 'Lowest date' in third_row.text_content()

    def _get_brief_response_dashboard_status(self, data_api_client, brief_response_status, brief_status):
        self.find_brief_responses_response = {
            'briefResponses': [
                {
                    'briefId': 1,
                    'brief': {
                        'title': 'Submitted brief response for open opportunity',
                        'applicationsClosedAt': '2017-06-09T10:26:21.538917Z',
                        'status': brief_status,
                        'frameworkSlug': 'digital-outcomes-and-specialists-2'
                    },
                    'status': brief_response_status,
                },
            ]
        }
        rows = self.get_table_rows_by_id('submitted-opportunities', data_api_client)
        return [row.getchildren()[2].text_content().strip() for row in rows][0]

    def test_submitted_brief_response_for_open_brief_shows_submitted_status(self, data_api_client):
        assert self._get_brief_response_dashboard_status(data_api_client, "submitted", "live") == "Submitted"

    def test_submitted_brief_response_for_closed_brief_shows_submitted_status(self, data_api_client):
        assert self._get_brief_response_dashboard_status(data_api_client, "submitted", "closed") == "Submitted"

    def test_submitted_brief_response_for_cancelled_brief_shows_cancelled_status(self, data_api_client):
        assert self._get_brief_response_dashboard_status(
            data_api_client, "submitted", "cancelled") == "Opportunity cancelled"

    def test_submitted_brief_response_for_unsuccessful_brief_shows_not_won_status(self, data_api_client):
        assert self._get_brief_response_dashboard_status(data_api_client, "submitted", "unsuccessful") == "Not won"

    def test_submitted_brief_response_for_withdrawn_brief_shows_withdrawn_status(self, data_api_client):
        assert self._get_brief_response_dashboard_status(
            data_api_client, "submitted", "withdrawn") == "Opportunity withdrawn"

    def test_brief_awarded_to_different_brief_response_shows_not_won_status(self, data_api_client):
        assert self._get_brief_response_dashboard_status(data_api_client, "submitted", "awarded") == "Not won"

    def test_pending_award_brief_response_for_closed_brief_shows_submitted_status(self, data_api_client):
        assert self._get_brief_response_dashboard_status(data_api_client, "pending-awarded", "closed") == "Submitted"

    def test_pending_award_brief_response_for_cancelled_brief_shows_not_won_status(self, data_api_client):
        assert self._get_brief_response_dashboard_status(
            data_api_client, "pending-awarded", "cancelled") == "Opportunity cancelled"

    def test_awarded_brief_response_shows_won_status(self, data_api_client):
        assert self._get_brief_response_dashboard_status(data_api_client, "awarded", "awarded") == "Won"
