###################################################################################
#
#    Copyright (C) 2020 Cetmix OÜ
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

from odoo.tests import HttpCase, tagged

from odoo.addons.prt_report_attachment_preview.controllers.report import (
    CxReportController,
)
from odoo.addons.website.tools import MockRequest


@tagged("post_install", "-at_install")
class TestCxReportController(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.controller = CxReportController()

    def test_get_extra_context_for_single_record(self):
        """
        Test the _get_extra_context_for_single_record method to ensure it correctly
        identifies and handles various expressions in the report name.
        """
        # Test case 1: Simple expression
        report_name = (
            "(object.state in ('draft', 'sent') and 'Quotation - %s' % (object.name)) "
            "or 'Order - %s' % (object.name)"
        )
        expected_result = {"object": "report"}
        result = self.controller._get_extra_context_for_single_record(report_name)
        self.assertEqual(
            result,
            expected_result,
            "Failed to correctly identify the variable in a simple expression.",
        )

        # Test case 2: Ignore expressions
        report_name = (
            "(object.state in ('draft', 'sent') and 'Quotation - %s' % (object.name)) "
            "or 'Order - %s' % (object.name)"
        )
        ignore_expr = ["object"]
        expected_result = {}
        result = self.controller._get_extra_context_for_single_record(
            report_name, ignore_expr=ignore_expr
        )
        self.assertEqual(
            result, expected_result, "Failed to correctly ignore specified expressions."
        )

        # Test case 3: No expressions
        report_name = "Simple Report Name"
        expected_result = {}
        result = self.controller._get_extra_context_for_single_record(report_name)
        self.assertEqual(
            result, expected_result, "Failed to handle report name with no expressions."
        )

    def test_compose_report_file_name(self):
        """
        Test the _compose_report_file_name method to ensure it correctly composes
        the report file name based on the provided document IDs and report action.
        """
        # Create a dummy report action for testing
        report_action = self.env["ir.actions.report"].create(
            {
                "name": "Test Report",
                "model": "res.partner",
                "report_type": "qweb-pdf",
                "report_name": "prt_report_attachment_preview.report_template",
                "print_report_name": '(object.name or "Unknown") + " Report"',
            }
        )
        test_partner_1 = self.env["res.partner"].create({"name": "Test Partner 1"})
        test_partner_2 = self.env["res.partner"].create({"name": "Test Partner 2"})

        # Test case 1: Valid print_report_name
        docids = [test_partner_1.id]
        with MockRequest(self.env):
            report_name = self.controller._compose_report_file_name(
                docids, report_action
            )
            self.assertIn(
                "Test Partner 1 Report",
                report_name,
                "Failed to compose the report file name correctly for a single record.",
            )

        # Test case 2: Valid print_report_name and several records
        docids.append(test_partner_2.id)
        with MockRequest(self.env):
            report_name = self.controller._compose_report_file_name(
                docids, report_action
            )
            self.assertIn(
                "Test Report x2",
                report_name,
                (
                    "Failed to compose the report"
                    " file name correctly for multiple records."
                ),
            )

        # Test case 3: Without docids
        with MockRequest(self.env):
            report_name = self.controller._compose_report_file_name([], report_action)
            self.assertIn(
                "Test Report",
                report_name,
                (
                    "Failed to compose the report file name"
                    " correctly when no docids are provided."
                ),
            )

        # Test case 4: Invalid print_report_name (non-string)
        # Set print_report_name to a non-string value
        report_action.print_report_name = False
        with MockRequest(self.env):
            report_name = self.controller._compose_report_file_name(
                docids, report_action
            )
            self.assertEqual(
                report_name,
                f"{report_action.name} x2",
                "Failed to handle non-string print_report_name correctly.",
            )
