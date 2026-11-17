import io
from PIL import Image
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from .models import Student, Item, Claim
from .similarity import calculate_image_similarity


def create_test_image(color=(255, 0, 0), size=(100, 100)):
    """Helper to generate in-memory test images."""
    file_obj = io.BytesIO()
    img = Image.new('RGB', size, color=color)
    img.save(file_obj, format='PNG')
    file_obj.seek(0)
    return file_obj


class SimilarityEngineTestCase(TestCase):
    def test_identical_image_similarity(self):
        img_io1 = create_test_image(color=(0, 100, 200))
        img_io2 = create_test_image(color=(0, 100, 200))

        result = calculate_image_similarity(img_io1, img_io2)
        self.assertIsNotNone(result['score'])
        self.assertGreaterEqual(result['score'], 95.0)
        self.assertEqual(result['result_badge'], 'match-high')
        self.assertTrue(result['has_reference'])

    def test_different_image_similarity(self):
        img_io1 = create_test_image(color=(255, 0, 0))
        img_io2 = create_test_image(color=(0, 255, 0))

        result = calculate_image_similarity(img_io1, img_io2)
        self.assertIsNotNone(result['score'])
        self.assertLess(result['score'], 80.0)

    def test_missing_reference_image(self):
        img_io = create_test_image(color=(128, 128, 128))
        result = calculate_image_similarity(img_io, None)
        self.assertIsNone(result['score'])
        self.assertFalse(result['has_reference'])
        self.assertEqual(result['result_badge'], 'match-na')


class HomepageViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_homepage_renders_successfully(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campus")
        self.assertContains(response, "Lost &amp; Found")
        self.assertContains(response, "Find")
        self.assertContains(response, "Claim")
        self.assertContains(response, "Reunite")
        self.assertContains(response, "Find Your Lost Item")
        self.assertContains(response, "Submit Claim")


class SubmitClaimViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = Student.objects.create(
            student_name="Test Student",
            email="teststudent@campus.edu",
            mobile_number="9876543210",
            department="Computer Science",
            roll_number="CS202601",
            password="testpassword"
        )

        test_img_bytes = create_test_image(color=(10, 50, 120)).getvalue()
        self.found_item = Item.objects.create(
            item_name="Blue Campus Backpack",
            category="Bags",
            description="Navy blue backpack found in library",
            location="Central Library",
            date=timezone.now(),
            item_type="Found",
            student=self.student,
            status="Active",
            image=SimpleUploadedFile("backpack.png", test_img_bytes, content_type="image/png")
        )

    def test_submit_claim_page_get(self):
        response = self.client.get(reverse('submit_claim'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Submit Item Claim")
        self.assertContains(response, "Student Information")
        self.assertContains(response, "Found Item Information")
        self.assertContains(response, "Blue Campus Backpack")

    def test_submit_claim_post_successful(self):
        lost_img_bytes = create_test_image(color=(10, 50, 120)).getvalue()
        lost_file = SimpleUploadedFile("my_lost_bag.png", lost_img_bytes, content_type="image/png")

        post_data = {
            'student': self.student.id,
            'item': self.found_item.id,
            'claim_description': "This is my blue college backpack with a small tear on the left strap.",
            'contact_number': "9876543210",
            'lost_date': "2026-11-01",
            'lost_location': "Central Library reading room",
            'additional_details': "Contains notebooks with CS notes",
            'lost_item_image': lost_file,
        }

        response = self.client.post(reverse('submit_claim'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        claim = Claim.objects.filter(student=self.student, item=self.found_item).first()
        self.assertIsNotNone(claim)
        self.assertEqual(claim.claim_status, "Pending")
        self.assertEqual(claim.lost_location, "Central Library reading room")
        self.assertIsNotNone(claim.similarity_score)
        self.assertGreaterEqual(claim.similarity_score, 80.0)

    def test_prevent_duplicate_claims(self):
        Claim.objects.create(
            student=self.student,
            item=self.found_item,
            claim_description="First claim",
            contact_number="9876543210",
            claim_status="Pending"
        )

        post_data = {
            'student': self.student.id,
            'item': self.found_item.id,
            'claim_description': "Duplicate attempt",
            'contact_number': "9876543210",
        }

        response = self.client.post(reverse('submit_claim'), post_data, follow=True)
        self.assertContains(response, "already submitted an active claim")
        self.assertEqual(Claim.objects.filter(student=self.student, item=self.found_item).count(), 1)


class CompareClaimImagesApiTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = Student.objects.create(
            student_name="Alice",
            email="alice@campus.edu",
            mobile_number="9123456789",
            department="Electrical",
            roll_number="EE202602"
        )
        test_img_bytes = create_test_image(color=(200, 50, 50)).getvalue()
        self.item = Item.objects.create(
            item_name="Red Water Bottle",
            category="Bottles",
            description="Steel bottle found near cafeteria",
            location="Cafeteria",
            date=timezone.now(),
            item_type="Found",
            student=self.student,
            status="Active",
            image=SimpleUploadedFile("bottle.png", test_img_bytes, content_type="image/png")
        )

    def test_compare_images_api_success(self):
        upload_bytes = create_test_image(color=(200, 50, 50)).getvalue()
        uploaded = SimpleUploadedFile("lost_bottle.png", upload_bytes, content_type="image/png")

        response = self.client.post(reverse('compare_claim_images'), {
            'item_id': self.item.id,
            'lost_image': uploaded
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIsNotNone(data['score'])
        self.assertGreaterEqual(data['score'], 80.0)
        self.assertIn('breakdown', data)
        self.assertIn('explanation', data)


class AdminClaimsWorkflowTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="campusadmin",
            email="admin@campus.edu",
            password="adminpassword123"
        )
        self.student = Student.objects.create(
            student_name="Bob",
            email="bob@campus.edu",
            mobile_number="9988776655",
            department="Mechanical",
            roll_number="ME202603"
        )
        self.item = Item.objects.create(
            item_name="Calculator",
            category="Electronics",
            description="Scientific calculator fx-991EX",
            location="Lab 3",
            date=timezone.now(),
            item_type="Found",
            student=self.student,
            status="Active"
        )
        self.claim = Claim.objects.create(
            student=self.student,
            item=self.item,
            claim_description="Has my name initials engraved on the back cover",
            contact_number="9988776655",
            claim_status="Pending"
        )

    def test_admin_approve_claim(self):
        self.client.login(username="campusadmin", password="adminpassword123")
        response = self.client.post(reverse('approve_claim', args=[self.claim.id]), {
            'admin_note': "Initials verified against student ID card."
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.claim.refresh_from_db()
        self.item.refresh_from_db()

        self.assertEqual(self.claim.claim_status, "Approved")
        self.assertEqual(self.claim.admin_note, "Initials verified against student ID card.")
        self.assertEqual(self.item.status, "Returned")

    def test_admin_reject_claim(self):
        self.client.login(username="campusadmin", password="adminpassword123")
        response = self.client.post(reverse('reject_claim', args=[self.claim.id]), {
            'admin_note': "Model does not match description."
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.claim_status, "Rejected")
        self.assertEqual(self.claim.admin_note, "Model does not match description.")
