import unittest
from unittest.mock import patch, MagicMock
from filmow_scraper import FilmowScraper
from requests.exceptions import HTTPError


class TestFilmowScraper(unittest.TestCase):
    def setUp(self):
        """Set up a FilmowScraper instance for testing."""
        self.scraper = FilmowScraper(
            user='test_user',
            max_retries=1,
            timeout=5
        )

    @patch('filmow_scraper.requests.Session.get')
    def test_get_count_of_pages_success(self, mock_get):
        """Test get_count_of_pages returns correct page count when successful."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<div class="pagination"><a>1</a><a>2</a><a>3</a></div>'
        mock_get.return_value = mock_response

        # Call method
        page_count = self.scraper.get_count_of_pages("ja-vi")
        self.assertEqual(page_count, 3)

    @patch('filmow_scraper.requests.Session.get')
    def test_get_count_of_pages_empty_pagination(self, mock_get):
        """Test get_count_of_pages raises ValueError when pagination is absent."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<div class="pagination"></div>'
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            self.scraper.get_count_of_pages("ja-vi")

    @patch('filmow_scraper.requests.Session.get')
    def test_get_count_of_pages_http_error(self, mock_get):
        """Test get_count_of_pages raises HTTPError when the request fails."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPError("HTTP error occurred")
        mock_get.return_value = mock_response

        with self.assertRaises(HTTPError):
            self.scraper.get_count_of_pages("favoritos")

    def test_media_item_to_dict(self):
        """Test that MediaItem's to_dict method works correctly."""
        media_item = self.scraper.MediaItem(
            title_portuguese="Filme Exemplo",
            title_original="Example Movie",
            user_rating=8.5,
            favorite=True
        )
        media_dict = media_item.to_dict()
        expected_dict = {
            'Título nacional': "Filme Exemplo",
            'Título original': "Example Movie",
            'Nota do usuário': 8.5,
            'Favorito': True
        }
        self.assertEqual(media_dict, expected_dict)

    @patch('filmow_scraper.requests.Session.get')
    def test_retry_strategy(self, mock_get):
        """Test that the retry strategy works as expected."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<div class="pagination"><a>1</a><a>2</a></div>'

        # Simulate a temporary failure (exception on first request, success on second)
        mock_get.side_effect = [Exception("Temporary failure"), mock_response]

        # Check that retry works correctly
        with self.assertLogs(self.scraper.logger, level='INFO') as log:
            page_count = self.scraper.get_count_of_pages("ja-vi")

        # Verify the response and logs
        self.assertEqual(page_count, 2)
        self.assertIn("Temporary failure", log.output[0])

    @patch('filmow_scraper.requests.Session.get')
    def test_to_watch_list_scraping(self, mock_get):
        """Test scraping of 'to-watch' movies from the user's Filmow profile."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
            <div class="movie">
                <a class="movie-title" href="example-url">Filme Exemplo</a>
                <span class="movie-original-title">Example Movie</span>
            </div>
        """
        mock_get.return_value = mock_response

        # Mock the get_count_of_pages method to simulate a single page
        self.scraper.get_count_of_pages = MagicMock(return_value=1)

        # Call the scraping method
        self.scraper.scrape_media_list = MagicMock(return_value=[
            self.scraper.MediaItem(
                title_portuguese="Filme Exemplo",
                title_original="Example Movie"
            )
        ])
        to_watch_items = self.scraper.scrape_media_list(self.scraper.TO_WATCH, self.scraper.MOVIES)

        # Verify the scraped items
        self.assertEqual(len(to_watch_items), 1)
        self.assertEqual(to_watch_items[0].title_portuguese, "Filme Exemplo")
        self.assertEqual(to_watch_items[0].title_original, "Example Movie")

    @patch('filmow_scraper.requests.Session.get')
    def test_watched_movies_scraping(self, mock_get):
        """Test scraping of 'watched movies' from the user's profile."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
            <div class="movie">
                <a class="movie-title" href="example-url">Filme Assistido</a>
                <span class="movie-original-title">Watched Movie</span>
            </div>
        """
        mock_get.return_value = mock_response

        # Mock the get_count_of_pages method to simulate a single page
        self.scraper.get_count_of_pages = MagicMock(return_value=1)

        # Call the scraping method
        self.scraper.scrape_media_list = MagicMock(return_value=[
            self.scraper.MediaItem(
                title_portuguese="Filme Assistido",
                title_original="Watched Movie"
            )
        ])
        watched_items = self.scraper.scrape_media_list(self.scraper.WATCHED, self.scraper.MOVIES)

        # Verify the scraped items
        self.assertEqual(len(watched_items), 1)
        self.assertEqual(watched_items[0].title_portuguese, "Filme Assistido")
        self.assertEqual(watched_items[0].title_original, "Watched Movie")


if __name__ == '__main__':
    unittest.main()
