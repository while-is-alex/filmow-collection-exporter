import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
import concurrent.futures
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class FilmowScraper:
    """
    A web scraper for extracting user media lists from Filmow.com.

    This class handles the fetching and parsing of a user's watched, favorite,
    and to-watch lists for both movies and TV shows from Filmow.com.

    Attributes:
        user (str): The Filmow username to scrape data for.
        base_url (str): The base URL for the user's profile.
        session (requests.Session): Session object for making HTTP requests.
        logger (logging.Logger): Logger for tracking scraping operations.
    """

    @dataclass
    class MediaItem:
        """Represents a media item (movie or TV show) from Filmow."""
        title_portuguese: str
        title_original: str
        user_rating: Optional[float] = None
        favorite: bool = False

        def to_dict(self) -> Dict[str, Any]:
            """Convert the media item to a dictionary."""
            result = {
                'Título nacional': self.title_portuguese,
                'Título original': self.title_original,
            }
            if self.user_rating is not None:
                result['Nota do usuário'] = self.user_rating
            if self.favorite:
                result['Favorito'] = self.favorite
            return result

    # Media type constants
    MOVIES = 'filmes'
    TV_SHOWS = 'series'

    # Category constants
    FAVORITES = 'favoritos'
    WATCHED = 'ja-vi'
    TO_WATCH = 'quero-ver'

    def __init__(self, user: str, max_retries: int = 5, timeout: int = 10, max_workers: int = 5):
        """
        Initialize the Filmow scraper.

        Args:
            user (str): Filmow username to scrape.
            max_retries (int): Maximum number of request retries.
            timeout (int): Request timeout in seconds.
            max_workers (int): Maximum number of concurrent worker threads.
        """
        self.user = user
        self.base_url = f'https://filmow.com/usuario/{self.user}'
        self.max_workers = max_workers

        self.logger = logging.getLogger(f'FilmowScraper-{user}')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET']
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount('http://', adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.timeout = timeout

        self.watched = []
        self.favorites = []
        self.to_watch = []

    def get_count_of_pages(self, url_suffix: str) -> int:
        """
        Determine the total number of pages for a given category.

        Args:
            url_suffix (str): The URL suffix for the category.

        Returns:
            int: Total number of pages.

        Raises:
            ValueError: If page count cannot be determined.
        """
        url = f'{self.base_url}/{url_suffix}/?pagina=1'

        try:
            response = self.session.get(
                url,
                timeout=self.timeout
            )
            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                'html.parser'
            )
            pages = soup.find(class_='pagination')

            if not pages:
                return 1  # Only one page available

            last_page = pages.find(title="última página")
            if last_page:
                last_page_href = last_page.get("href")
                return int(last_page_href.split("=")[1])

            # Alternative way to find the last page
            pagination = soup.find(
                'div',
                class_='pagination pagination-centered'
            )
            if pagination:
                list_elements = pagination.find_all('li')
                if list_elements:
                    for element in reversed(list_elements):
                        a_tag = element.find('a')
                        if a_tag and a_tag.get('href') and '?pagina=' in a_tag['href']:
                            return int(a_tag['href'].split('=')[1])

            # If we can't find pagination but there are items, assume one page
            if soup.select('.movie_list_item'):
                return 1

            raise ValueError(f"Could not determine page count for {url_suffix}")

        except (requests.RequestException, ValueError) as e:
            self.logger.error(f'Error getting page count for {url_suffix}: {str(e)}')
            return 1  # Default to 1 page if there's an error

    def extract_title_info(self, full_title: str) -> Tuple[str, str]:
        """
        Extract Portuguese and original titles from the full title string.

        Args:
            full_title (str): The full title string from Filmow.

        Returns:
            Tuple[str, str]: A tuple containing (portuguese_title, original_title).
        """
        try:
            # Handle TV show seasons format
            if 'Temporada)' in full_title:
                parts = full_title.split(') ')
                portuguese_title = parts[0] + ')'
                # Handle case where there's no original title
                if len(parts) > 1:
                    original_title = parts[1][1:-1] if parts[1].startswith('(') else parts[1]
                else:
                    original_title = portuguese_title
            # Handle standard movie format
            elif ' (' in full_title and full_title.endswith(')'):
                portuguese_title = full_title.split(' (')[0]
                original_title = full_title.split(' (')[1][:-1]
            # Fallback for unexpected formats
            else:
                portuguese_title = full_title
                original_title = full_title

            return portuguese_title.strip(), original_title.strip()

        except Exception as e:
            self.logger.warning(f'Error parsing title "{full_title}": {str(e)}')
            return full_title, full_title

    def extract_user_rating(self, item_soup) -> Optional[float]:
        """
        Extract user rating from a media item.

        Args:
            item_soup (BeautifulSoup): BeautifulSoup object for the media item.

        Returns:
            Optional[float]: User rating as float, or None if not found.
        """
        span_element = item_soup.find(
            'span',
            class_='tip star-rating star-rating-small stars'
        )
        if span_element and span_element.get('title'):
            try:
                title_value = span_element.get('title')
                # Extract the numerical rating
                rating_parts = title_value.split()
                if len(rating_parts) > 1:
                    return float(rating_parts[1].replace(',', '.'))
            except (ValueError, IndexError) as e:
                self.logger.warning(f"Error parsing rating: {str(e)}")

        return None

    def parse_media_item(self, item, category: str) -> MediaItem:
        """
        Parse a single media item from the page.

        Args:
            item (BeautifulSoup): BeautifulSoup object for the media item.
            category (str): Category of the media item (favorites, watched, to-watch).

        Returns:
            MediaItem: Parsed media item.
        """
        # Extract title
        img_element = item.find(
            'span',
            class_='wrapper'
        )
        if not img_element:
            self.logger.warning('Wrapper span not found in item')
            return None

        img = img_element.find('img')
        if not img:
            self.logger.warning('Image not found in wrapper span')
            return None

        full_title = img.get(
            'alt',
            ''
        )
        if not full_title:
            self.logger.warning('Alt attribute not found or empty in image')
            return None

        portuguese_title, original_title = self.extract_title_info(full_title)

        # Extract rating for watched or favorites
        user_rating = None
        if category in [self.WATCHED, self.FAVORITES]:
            user_rating = self.extract_user_rating(item)

        # Create media item
        return self.MediaItem(
            title_portuguese=portuguese_title,
            title_original=original_title,
            user_rating=user_rating,
            favorite=(category == self.FAVORITES)
        )

    def process_media_page(self, media_type: str, category: str, page_number: int) -> List[MediaItem]:
        """
        Process a single page of media items.

        Args:
            media_type (str): Type of media (movies or TV shows).
            category (str): Category of media items.
            page_number (int): Page number to process.

        Returns:
            List[MediaItem]: List of parsed media items.
        """
        url = f'{self.base_url}/{media_type}/{category}/?pagina={page_number}'
        result = []

        try:
            response = self.session.get(
                url,
                timeout=self.timeout
            )
            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                'html.parser'
            )
            media_list = soup.select('.movie_list_item')

            for item in media_list:
                media_item = self.parse_media_item(
                    item,
                    category
                )
                if media_item:
                    result.append(media_item)

        except requests.RequestException as e:
            self.logger.error(f'Error fetching page {page_number} for {media_type}/{category}: {str(e)}')
        except Exception as e:
            self.logger.error(f'Error processing page {page_number} for {media_type}/{category}: {str(e)}')

        return result

    def get_media_category(self, media_type: str, category: str) -> List[Dict[str, Any]]:
        """
        Get all media items for a specific type and category.

        Args:
            media_type (str): Type of media (movies or TV shows).
            category (str): Category of media items.

        Returns:
            List[Dict[str, Any]]: List of media items as dictionaries.
        """
        try:
            page_count = self.get_count_of_pages(f'{media_type}/{category}')
            self.logger.info(f'Extracting {media_type} (category {category}). {page_count} pages detected.')

            all_items = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_page = {
                    executor.submit(self.process_media_page, media_type, category, page): page
                    for page in range(1, page_count + 1)
                }

                for future in tqdm(
                        concurrent.futures.as_completed(future_to_page),
                        total=len(future_to_page),
                        desc=f'{media_type}/{category}'
                ):
                    page = future_to_page[future]
                    try:
                        items = future.result()
                        all_items.extend(items)
                    except Exception as e:
                        self.logger.error(f'Error processing page {page}: {str(e)}')

            return [item.to_dict() for item in all_items]

        except Exception as e:
            self.logger.error(f'Error getting {media_type}/{category}: {str(e)}')
            return []

    def get_media(self, media_type: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Get all media items of a specific type (movies or TV shows).

        Args:
            media_type (str): Type of media to fetch (MOVIES or TV_SHOWS).

        Returns:
            Tuple[List[Dict], List[Dict], List[Dict]]: Watched, favorites, and to-watch lists.
        """
        if media_type not in [self.MOVIES, self.TV_SHOWS]:
            raise ValueError(f'Invalid media type: {media_type}. Use MOVIES or TV_SHOWS.')

        # Reset lists
        self.watched = []
        self.favorites = []
        self.to_watch = []

        # Get favorites first to identify them in the watched list
        self.favorites = self.get_media_category(
            media_type,
            self.FAVORITES
        )

        # Get watched items and mark favorites
        watched_items = self.get_media_category(
            media_type,
            self.WATCHED
        )

        # Mark favorites in watched list
        favorite_titles = {(item['Título nacional'], item['Título original']) for item in self.favorites}

        for item in watched_items:
            if (item['Título nacional'], item['Título original']) in favorite_titles:
                item['Favorito'] = True
            else:
                item['Favorito'] = False

        self.watched = watched_items

        # Get to-watch items
        self.to_watch = self.get_media_category(
            media_type,
            self.TO_WATCH
        )

        return self.watched, self.favorites, self.to_watch

    def get_all_media(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Get all media items (both movies and TV shows).

        Returns:
            Dict: Dictionary containing all media lists categorized by type and category.
        """
        result = {
            'movies': {},
            'tv_shows': {}
        }

        self.logger.info('Fetching movies...')
        movies_watched, movies_favorites, movies_to_watch = self.get_media(self.MOVIES)
        result['movies']['watched'] = movies_watched
        result['movies']['favorites'] = movies_favorites
        result['movies']['to_watch'] = movies_to_watch

        self.logger.info('Fetching TV shows...')
        tv_watched, tv_favorites, tv_to_watch = self.get_media(self.TV_SHOWS)
        result['tv_shows']['watched'] = tv_watched
        result['tv_shows']['favorites'] = tv_favorites
        result['tv_shows']['to_watch'] = tv_to_watch

        return result

    def save_to_csv(self, filename_prefix: str = None):
        """
        Save all media lists to CSV files.

        Args:
            filename_prefix (str, optional): Prefix for saved filenames.
        """
        import pandas as pd
        import os

        if filename_prefix is None:
            filename_prefix = f'filmow_{self.user}_'

        os.makedirs(
            'output',
            exist_ok=True
        )

        # Get all media
        all_media = self.get_all_media()

        # Save each list to a separate CSV file
        for media_type, categories in all_media.items():
            for category, items in categories.items():
                if items:
                    df = pd.DataFrame(items)
                    filepath = f'output/{filename_prefix}{media_type}_{category}.csv'
                    df.to_csv(
                        filepath,
                        index=False,
                        encoding='utf-8-sig'
                    )
                    self.logger.info(f'Saved {len(items)} items to {filepath}')
