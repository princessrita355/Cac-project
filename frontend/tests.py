from django.test import TestCase
from django.urls import reverse


# Test that the frontend page which is the index page can load correctly

class FrontendViewTests(TestCase):

    def test_home_page_loads(self):
        """
        Home page should load successfully.
        """
        response = self.client.get(reverse("frontend:home"))

        self.assertEqual(response.status_code, 200)

    def test_home_page_uses_correct_template(self):
        """
        Home page should use frontend/index.html.
        """
        response = self.client.get(reverse("frontend:home"))

        self.assertTemplateUsed(response, "frontend/index.html")