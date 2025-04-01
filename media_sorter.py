from typing import List, Dict, Any, Union, Callable, Optional, TypeVar, cast
from functools import cmp_to_key

T = TypeVar(
    'T',
    bound=Dict[str, Any]
)


class MediaSorter:
    """
    A utility class for sorting media collections such as movies or TV shows.

    This class provides methods to sort lists of dictionaries representing media items
    by various criteria including title, rating, and favorite status, with support for
    customized sorting logic and multiple sorting keys.
    """

    @staticmethod
    def sort_by_title(
            media_list: List[T],
            title_key: str = 'Título nacional',
            reverse: bool = False
    ) -> List[T]:
        """
        Sort a list of media items alphabetically by title.

        Args:
            media_list: List of dictionaries representing media items.
            title_key: Dictionary key to use for sorting (default: 'Título nacional').
            reverse: If True, sort in descending order (default: False).

        Returns:
            A new sorted list of media items.

        Raises:
            KeyError: If any item in the list is missing the specified title_key.
        """
        if not media_list:
            return []

        # Validate that all items have the required key
        if any(title_key not in item for item in media_list):
            missing_keys = [i for i, item in enumerate(media_list) if title_key not in item]
            raise KeyError(
                f'Missing "{title_key}" key in {len(missing_keys)} items at positions: '
                f'{missing_keys[:5]}{"..." if len(missing_keys) > 5 else ""}'
            )

        # Create a case-insensitive sorting function that handles None values
        def get_sort_key(item: T) -> str:
            value = item.get(title_key)
            if value is None:
                return ''
            return str(value).lower()

        return sorted(
            media_list,
            key=get_sort_key,
            reverse=reverse
        )

    @staticmethod
    def sort_by_rating(
            media_list: List[T],
            rating_key: str = 'Nota do usuário',
            reverse: bool = True
    ) -> List[T]:
        """
        Sort a list of media items by their rating.

        Args:
            media_list: List of dictionaries representing media items.
            rating_key: Dictionary key to use for rating (default: 'Nota do usuário').
            reverse: If True, sort in descending order (default: True).

        Returns:
            A new sorted list of media items.
        """
        if not media_list:
            return []

        def parse_rating(item: T) -> float:
            """Convert rating value to float, handling various formats and None values."""
            rating = item.get(rating_key)

            if rating is None or rating == 'None' or rating == '':
                return 0.0

            try:
                # Handle both string and numeric types
                if isinstance(rating, (int, float)):
                    return float(rating)

                # Handle comma as decimal separator
                rating_str = str(rating).replace(
                    ',',
                    '.'
                )
                return float(rating_str)
            except (ValueError, TypeError):
                return 0.0

        return sorted(
            media_list,
            key=parse_rating,
            reverse=reverse
        )

    @staticmethod
    def sort_by_favorite(
            media_list: List[T],
            favorite_key: str = 'Favorito',
            reverse: bool = True
    ) -> List[T]:
        """
        Sort a list of media items by their favorite status.

        Args:
            media_list: List of dictionaries representing media items.
            favorite_key: Dictionary key to use for favorite status (default: 'Favorito').
            reverse: If True, favorites come first (default: True).

        Returns:
            A new sorted list of media items.
        """
        if not media_list:
            return []

        def get_favorite_status(item: T) -> int:
            """Convert favorite status to integer for sorting."""
            favorite = item.get(
                favorite_key,
                False
            )

            # Handle different ways favorite status might be stored
            if isinstance(favorite, bool):
                return 1 if favorite else 0
            elif isinstance(favorite, (int, float)):
                return 1 if favorite > 0 else 0
            elif isinstance(favorite, str):
                lower_str = favorite.lower()
                if lower_str in ('true', 'yes', 'sim', '1', 'favorite', 'favorito'):
                    return 1
                else:
                    return 0
            else:
                return 0

        return sorted(
            media_list,
            key=get_favorite_status,
            reverse=reverse
        )

    @staticmethod
    def sort_multiple_lists(
            lists: List[List[T]],
            sort_method: Callable[[List[T]], List[T]]
    ) -> List[List[T]]:
        """
        Apply the same sorting method to multiple lists.

        Args:
            lists: A list of lists, each containing media items.
            sort_method: A function that sorts a single list.

        Returns:
            A list of sorted lists.
        """
        return [sort_method(media_list.copy()) if media_list else [] for media_list in lists]

    @staticmethod
    def sort_by_multiple_keys(
            media_list: List[T],
            sort_keys: List[Dict[str, Any]]
    ) -> List[T]:
        """
        Sort a list of media items by multiple criteria in order of priority.

        Args:
            media_list: List of dictionaries representing media items.
            sort_keys: List of sorting configurations, each a dict with:
                - 'key': The dictionary key to sort by
                - 'reverse': Boolean indicating reverse sort (optional)
                - 'type': Type of sort ('string', 'numeric', 'boolean') (optional)

        Returns:
            A new sorted list of media items.

        Example:
            Sort by favorite status (descending), then by rating (descending), then by title:
            sort_keys = [
                {'key': 'Favorito', 'reverse': True, 'type': 'boolean'},
                {'key': 'Nota do usuário', 'reverse': True, 'type': 'numeric'},
                {'key': 'Título nacional', 'reverse': False, 'type': 'string'}
            ]
        """
        if not media_list or not sort_keys:
            return media_list

        def compare_items(item1: T, item2: T) -> int:
            """Compare two items based on multiple sort keys."""
            for sort_config in sort_keys:
                key = sort_config['key']
                reverse = sort_config.get(
                    'reverse',
                    False
                )
                sort_type = sort_config.get(
                    'type',
                    'string'
                )

                val1 = item1.get(key)
                val2 = item2.get(key)

                if val1 is None and val2 is None:
                    continue
                if val1 is None:
                    return 1 if reverse else -1
                if val2 is None:
                    return -1 if reverse else 1

                if sort_type == 'numeric':
                    # Convert to float for numeric comparison
                    try:
                        num1 = float(str(val1).replace(',', '.')) if isinstance(val1, (str, int, float)) else 0.0
                        num2 = float(str(val2).replace(',', '.')) if isinstance(val2, (str, int, float)) else 0.0

                        if num1 < num2:
                            return 1 if reverse else -1
                        if num1 > num2:
                            return -1 if reverse else 1
                    except (ValueError, TypeError):
                        # If conversion fails, fall back to string comparison
                        pass

                elif sort_type == 'boolean':
                    # Convert to boolean equivalents
                    bool1 = val1 in (True, 1, '1', 'true', 'True', 'yes', 'Yes', 'sim', 'Sim')
                    bool2 = val2 in (True, 1, '1', 'true', 'True', 'yes', 'Yes', 'sim', 'Sim')

                    if bool1 != bool2:
                        if bool1:
                            return -1 if reverse else 1
                        else:
                            return 1 if reverse else -1
                else:
                    str1 = str(val1).lower()
                    str2 = str(val2).lower()

                    if str1 < str2:
                        return 1 if reverse else -1
                    if str1 > str2:
                        return -1 if reverse else 1

            # All keys equal
            return 0

        return sorted(
            media_list,
            key=cmp_to_key(compare_items)
        )
