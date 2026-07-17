import os
import json
import unittest
from app import app, load_issues, save_issues, load_crowd_data, save_crowd_data

class FanPathAITestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        # Back up existing database files
        self.issues_backup_path = 'issues_backup.json'
        self.crowd_backup_path = 'mock_crowd_backup.json'
        
        if os.path.exists('issues.json'):
            os.rename('issues.json', self.issues_backup_path)
        if os.path.exists('mock_crowd_data.json'):
            os.rename('mock_crowd_data.json', self.crowd_backup_path)
            
        # Write clean mock data
        save_issues([])
        save_crowd_data({
            "Gate A": "Medium",
            "Gate B": "Low",
            "Food Court": "High",
            "Parking": "Medium",
            "Main Stand": "Low"
        })

    def tearDown(self):
        # Restore backups
        if os.path.exists('issues.json'):
            os.remove('issues.json')
        if os.path.exists('mock_crowd_data.json'):
            os.remove('mock_crowd_data.json')
            
        if os.path.exists(self.issues_backup_path):
            os.rename(self.issues_backup_path, 'issues.json')
        if os.path.exists(self.crowd_backup_path):
            os.rename(self.crowd_backup_path, 'mock_crowd_data.json')

    def test_home_page(self):
        """Test that the homepage loads successfully and contains title text."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'FanPath AI', response.data)
        self.assertIn(b'Assistant', response.data)

    def test_dashboard_page(self):
        """Test that the crowd dashboard page loads and displays status cards."""
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Crowd Density', response.data)
        self.assertIn(b'Gate A', response.data)

    def test_crowd_update_api(self):
        """Test the crowd simulation update API."""
        response = self.client.post('/api/crowd/update')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('Gate A', data['data'])

    def test_chat_fallback(self):
        """Test the AI chat endpoint fallback mechanism."""
        payload = {
            "message": "Where is Gate A?",
            "history": []
        }
        response = self.client.post('/chat', 
                                    data=json.dumps(payload),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('reply', data)
        self.assertTrue(len(data['reply']) > 0)

    def test_report_page_get(self):
        """Test that the issue reporting form loads successfully."""
        response = self.client.get('/report')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Report a Stadium', response.data)

    def test_report_submission_post(self):
        """Test submitting a new issue report."""
        form_data = {
            'reporter_name': 'Test Volunteer',
            'zone': 'Gate A',
            'category': 'Maintenance',
            'description': 'Broken light fixture in tunnel.'
        }
        response = self.client.post('/report', data=form_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'reported successfully', response.data)
        
        # Verify it was saved to database
        issues = load_issues()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]['reporter_name'], 'Test Volunteer')
        self.assertEqual(issues[0]['description'], 'Broken light fixture in tunnel.')

    def test_admin_console(self):
        """Test that the admin page loads and displays reported issues."""
        # Insert a mock issue
        issues = [{
            "id": "tst123",
            "reporter_name": "Admin Tester",
            "zone": "Food Court",
            "category": "Safety",
            "description": "Slippery floor near beverage stand.",
            "timestamp": "2026-07-13 12:00:00",
            "status": "Open"
        }]
        save_issues(issues)
        
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Slippery floor', response.data)
        self.assertIn(b'Admin Tester', response.data)

    def test_admin_resolve_and_delete(self):
        """Test resolving and deleting an issue via admin routes."""
        issue_id = "abc456"
        issues = [{
            "id": issue_id,
            "reporter_name": "Issue Tester",
            "zone": "Parking",
            "category": "Other",
            "description": "Signage knocked down.",
            "timestamp": "2026-07-13 12:00:00",
            "status": "Open"
        }]
        save_issues(issues)
        
        # 1. Resolve issue
        response = self.client.post(f'/admin/resolve/{issue_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        updated_issues = load_issues()
        self.assertEqual(updated_issues[0]['status'], 'Resolved')
        
        # 2. Delete issue
        response = self.client.post(f'/admin/delete/{issue_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        final_issues = load_issues()
        self.assertEqual(len(final_issues), 0)

if __name__ == '__main__':
    unittest.main()
