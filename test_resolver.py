"""Test script for LinkTreeResolver."""

import unittest
from unittest.mock import patch, MagicMock
from link_tree_resolver import LinkTreeResolver

class TestLinkTreeResolver(unittest.TestCase):
    
    def setUp(self):
        self.resolver = LinkTreeResolver()
        
    def test_is_link_tree(self):
        """Test detection of link tree services."""
        self.assertTrue(self.resolver.is_link_tree('https://linktr.ee/someuser'))
        self.assertTrue(self.resolver.is_link_tree('https://bio.link/user'))
        self.assertTrue(self.resolver.is_link_tree('https://beacons.ai/creator'))
        self.assertFalse(self.resolver.is_link_tree('https://google.com'))
        self.assertFalse(self.resolver.is_link_tree('https://mysite.com'))
        
    @patch('requests.get')
    def test_resolve_url(self, mock_get):
        """Test resolving a link tree URL."""
        # Mock HTML content
        html_content = """
        <html>
            <body>
                <a href="https://instagram.com/user">Instagram</a>
                <a href="https://twitter.com/user">Twitter</a>
                <a href="https://mybusiness.com">My Website</a>
                <a href="https://shop.mybusiness.com">Shop</a>
                <a href="mailto:email@example.com">Email</a>
                <a href="#">Invalid</a>
            </body>
        </html>
        """
        
        mock_response = MagicMock()
        mock_response.text = html_content
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        results = self.resolver.resolve_url('https://linktr.ee/user')
        
        # Check social links
        self.assertIn('https://instagram.com/user', results['social_links'])
        self.assertIn('https://twitter.com/user', results['social_links'])
        
        # Check website links
        self.assertIn('https://mybusiness.com', results['website_links'])
        self.assertIn('https://shop.mybusiness.com', results['website_links'])
        
        # Check exclusions
        self.assertNotIn('mailto:email@example.com', results['website_links'])
        self.assertNotIn('#', results['website_links'])

if __name__ == '__main__':
    unittest.main()
