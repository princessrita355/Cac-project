from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.urls import reverse
from django.contrib.messages import get_messages
from .models import Application
from unittest.mock import patch

#Testing the Business Logic

class ApplicationModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="john@example.com",
            email="john@example.com",
            password="password123"
        )

        image = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00"
            b"\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
            b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00"
            b"\x00\x00\x01\x00\x01\x00\x00\x02\x02"
            b"\x44\x01\x00;"
        )

        self.app = Application.objects.create(
            user=self.user,
            proposed_name_1="TECH WORLD",
            proposed_name_2="",
            nature_of_business="Technology",
            business_type="Enterprise",
            state="CROSS RIVER",
            lga="CALABAR",
            business_address="NO 10 PALM STREET",
            owner_first_name="John",
            owner_last_name="Doe",
            owner_email="owner@example.com",
            owner_phone="08012345678",
            passport=SimpleUploadedFile(
                "passport.gif",
                image,
                content_type="image/gif"
            ),
            signature=SimpleUploadedFile(
                "signature.gif",
                image,
                content_type="image/gif"
            ),
            nin=SimpleUploadedFile(
                "nin.pdf",
                b"Dummy PDF",
                content_type="application/pdf"
            ),
        )

    def test_application_created(self):
        """Application should be created successfully."""
        self.assertEqual(Application.objects.count(), 1)

    def test_reference_id_generated(self):
        """Reference ID should be generated automatically."""
        self.assertTrue(self.app.reference_id.startswith("BN-"))

    def test_registration_number_generation(self):
        """Registration number should start with RC-."""
        self.app.generate_registration_number()

        self.assertTrue(
            self.app.registration_number.startswith("RC-")
        )

    def test_signature_generation(self):
        """Digital signature should be generated."""
        self.app.registration_number = "RC-12345678"
        self.app.approved_at = timezone.now()

        self.app.generate_signature()

        self.assertEqual(
            len(self.app.digital_signature),
            64
        )

    def test_verification_token_generation(self):
        """Verification token should be generated."""
        self.app.registration_number = "RC-12345678"

        self.app.generate_verification_token()

        self.assertEqual(
            len(self.app.verification_token),
            64
        )

    def test_add_query_note(self):
        """Application should become queried."""
        self.app.add_query_note("Upload clearer passport")

        self.assertEqual(
            self.app.status,
            Application.Status.QUERIED
        )

        self.assertEqual(
            self.app.agent_note,
            "Upload clearer passport"
        )

    def test_clear_query_note(self):
        """Clearing a query should reset status."""
        self.app.add_query_note("Fix address")

        self.app.clear_query_note()

        self.assertEqual(
            self.app.status,
            Application.Status.PENDING
        )

        self.assertEqual(
            self.app.agent_note,
            ""
        )

    def test_string_representation(self):
        """__str__ should contain reference id and business name."""
        self.assertEqual(
            str(self.app),
            f"{self.app.reference_id} - {self.app.proposed_name_1}"
        )



# Test views Logic
class ApplicationViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="john@example.com",
            email="john@example.com",
            password="password123"
        )

        self.client.login(
            username="john@example.com",
            password="password123"
        )

        image = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00"
            b"\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
            b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00"
            b"\x00\x00\x01\x00\x01\x00\x00\x02\x02"
            b"\x44\x01\x00;"
        )

        self.passport = SimpleUploadedFile(
            "passport.gif",
            image,
            content_type="image/gif"
        )

        self.signature = SimpleUploadedFile(
            "signature.gif",
            image,
            content_type="image/gif"
        )

        self.nin = SimpleUploadedFile(
            "nin.pdf",
            b"dummy pdf",
            content_type="application/pdf"
        )

    def test_start_application_requires_login(self):
        self.client.logout()

        response = self.client.get(
            reverse("applications:start")
        )

        self.assertEqual(response.status_code, 302)

    def test_start_application_page_loads(self):
        response = self.client.get(
            reverse("applications:start")
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "applications/application.html"
        )

    def test_submit_application_successfully(self):

        response = self.client.post(
          reverse("applications:start"),
        {
        "proposed_name_1": "Tech Hub",
        "proposed_name_2": "",
        "nature_of_business": "Technology",
        "business_type": "Enterprise",
        "state": "Cross River",
        "lga": "Calabar",
        "business_address": "Palm Street",
        "owner_first_name": "John",
        "owner_last_name": "Doe",
        "owner_email": "owner@test.com",
        "owner_phone": "08012345678",
        "business_description": "Software Company",
        "confirm": "on",

        # Put the files HERE
        "passport": self.passport,
        "signature": self.signature,
        "nin": self.nin,
    },
        follow=True,
    )

        self.assertEqual(
            Application.objects.count(),
            1
        )

    def test_save_application_as_draft(self):

        response = self.client.post(
            reverse("applications:start"),
            {
                "save_as_draft": "1"
            },
            follow=True
        )

        app = Application.objects.first()

        self.assertEqual(
            app.status,
            Application.Status.PENDING
        )

    def test_missing_required_fields(self):

        response = self.client.post(
            reverse("applications:start"),
            {},
            follow=True
        )

        self.assertEqual(
            Application.objects.count(),
            0
        )

    def test_my_application_api_returns_json(self):

        Application.objects.create(
            user=self.user,
            proposed_name_1="ABC LTD",
            proposed_name_2="",
            nature_of_business="Retail",
            business_type="Business",
            state="CR",
            lga="Calabar",
            business_address="Street",
            owner_first_name="John",
            owner_last_name="Doe",
            owner_email="abc@test.com",
            owner_phone="08012345678",
            passport=self.passport,
            signature=self.signature,
            nin=self.nin,
        )

        response = self.client.get(
            reverse("applications:api_mine")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertIn(
            "applications",
            response.json()
        )

    def test_api_returns_only_logged_in_users_applications(self):

        other = User.objects.create_user(
            username="mary@test.com",
            password="password123"
        )

        Application.objects.create(
            user=self.user,
            proposed_name_1="MINE",
            proposed_name_2="",
            nature_of_business="Retail",
            business_type="Business",
            state="CR",
            lga="Calabar",
            business_address="Street",
            owner_first_name="John",
            owner_last_name="Doe",
            owner_email="mine@test.com",
            owner_phone="08012345678",
            passport=self.passport,
            signature=self.signature,
            nin=self.nin,
        )

        Application.objects.create(
            user=other,
            proposed_name_1="NOT MINE",
            proposed_name_2="",
            nature_of_business="Retail",
            business_type="Business",
            state="CR",
            lga="Calabar",
            business_address="Street",
            owner_first_name="Mary",
            owner_last_name="Doe",
            owner_email="mary@test.com",
            owner_phone="08099999999",
            passport=SimpleUploadedFile(
                "passport2.gif",
                self.passport.read(),
                content_type="image/gif",
            ),
            signature=SimpleUploadedFile(
                "signature2.gif",
                self.signature.read(),
                content_type="image/gif",
            ),
            nin=SimpleUploadedFile(
                "nin2.pdf",
                b"dummy",
                content_type="application/pdf",
            ),
        )

        response = self.client.get(
            reverse("applications:api_mine")
        )

        data = response.json()["applications"]

        self.assertEqual(
            len(data),
            1
        )

    def test_api_requires_login(self):

        self.client.logout()

        response = self.client.get(
            reverse("applications:api_mine")
        )

        self.assertEqual(
            response.status_code,
            302
        )

#--------- verification workflow------
class ApplicationWorkflowTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="john@example.com",
            email="john@example.com",
            password="password123"
        )

        image = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00"
            b"\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
            b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00"
            b"\x00\x00\x01\x00\x01\x00\x00\x02\x02"
            b"\x44\x01\x00;"
        )

        self.app = Application.objects.create(
            user=self.user,
            proposed_name_1="TECH WORLD",
            proposed_name_2="",
            nature_of_business="Technology",
            business_type="Enterprise",
            state="CR",
            lga="CALABAR",
            business_address="ADDRESS",
            owner_first_name="John",
            owner_last_name="Doe",
            owner_email="owner@test.com",
            owner_phone="08012345678",
            passport=SimpleUploadedFile(
                "passport.gif",
                image,
                content_type="image/gif"
            ),
            signature=SimpleUploadedFile(
                "signature.gif",
                image,
                content_type="image/gif"
            ),
            nin=SimpleUploadedFile(
                "nin.pdf",
                b"pdf",
                content_type="application/pdf"
            ),
        )

    @patch("applications.models.Application.generate_and_save_certificate")
    @patch("applications.models.Application.generate_qr_code")
    def test_application_approval(
        self,
        mock_qr,
        mock_pdf
    ):
        self.app.approve()

        self.assertEqual(
            self.app.status,
            Application.Status.APPROVED
        )

    @patch("applications.models.Application.generate_and_save_certificate")
    @patch("applications.models.Application.generate_qr_code")
    def test_registration_number_created(
        self,
        mock_qr,
        mock_pdf
    ):
        self.app.approve()

        self.assertTrue(
            self.app.registration_number.startswith("RC-")
        )

    @patch("applications.models.Application.generate_and_save_certificate")
    @patch("applications.models.Application.generate_qr_code")
    def test_verification_token_created(
        self,
        mock_qr,
        mock_pdf
    ):
        self.app.approve()

        self.assertEqual(
            len(self.app.verification_token),
            64
        )

    @patch("applications.models.Application.generate_and_save_certificate")
    @patch("applications.models.Application.generate_qr_code")
    def test_signature_created(
        self,
        mock_qr,
        mock_pdf
    ):
        self.app.approve()

        self.assertEqual(
            len(self.app.digital_signature),
            64
        )

    def test_modify_only_when_queried(self):
        self.assertNotEqual(
            self.app.status,
            Application.Status.QUERIED
        )

    def test_reference_id_is_unique(self):

        image = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00"
            b"\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
            b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00"
            b"\x00\x00\x01\x00\x01\x00\x00\x02\x02"
            b"\x44\x01\x00;"
        )

        app2 = Application.objects.create(
            user=self.user,
            proposed_name_1="ABC LTD",
            proposed_name_2="",
            nature_of_business="Retail",
            business_type="Business",
            state="CR",
            lga="CALABAR",
            business_address="ADDRESS",
            owner_first_name="Jane",
            owner_last_name="Doe",
            owner_email="jane@test.com",
            owner_phone="08099999999",
            passport=SimpleUploadedFile(
                "passport2.gif",
                image,
                content_type="image/gif"
            ),
            signature=SimpleUploadedFile(
                "signature2.gif",
                image,
                content_type="image/gif"
            ),
            nin=SimpleUploadedFile(
                "nin2.pdf",
                b"pdf",
                content_type="application/pdf"
            ),
        )

        self.assertNotEqual(
            self.app.reference_id,
            app2.reference_id
        )

    def test_default_status_is_submitted(self):

        self.assertEqual(
            self.app.status,
            Application.Status.SUBMITTED
        )

    def test_query_note_history(self):

        self.app.add_query_note("First Query")
        self.app.add_query_note("Second Query")

        self.assertEqual(
            len(self.app.previous_notes),
            1
        )