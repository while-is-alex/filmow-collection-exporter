#!/usr/bin/env python3
"""
Filmow Media Collection Exporter

This script extracts a user's movie and TV show collections from Filmow.com,
sorts them by various criteria, and exports them to multiple file formats.
"""

import subprocess
import sys
import os
import json
import time
import argparse
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


def setup_logger(log_level: str = 'INFO') -> logging.Logger:
    """
    Configure and return a logger for the application.

    Args:
        log_level: Desired logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logging.Logger instance
    """
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=getattr(
            logging,
            log_level
        ),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                'filmow_export.log',
                mode='w'
            )
        ]
    )
    return logging.getLogger('FilmowExporter')


def check_and_install_dependencies() -> None:
    """
    Check for required dependencies and install them if missing.
    """
    required_packages = [
        'requests',
        'pandas',
        'beautifulsoup4',
        'tqdm',
        'openpyxl',
        'colorama',
        'argparse'
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f'Installing missing dependencies: {", ".join(missing_packages)}')
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install'] + missing_packages,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print('Dependencies installed successfully.')
        except subprocess.CalledProcessError as e:
            print(f'Error installing dependencies: {e}')
            print('Please install the following packages manually:')
            print(', '.join(missing_packages))
            sys.exit(1)


def import_dependencies():
    """
    Import dependencies after ensuring they're installed.
    Returns imported modules for use in the script.
    """
    global pd, tqdm, colorama

    import pandas as pd
    from tqdm import tqdm
    import colorama

    # Initialize colorama for cross-platform colored terminal output
    colorama.init()

    # Import local modules
    try:
        from filmow_scraper import FilmowScraper
        from media_sorter import MediaSorter
    except ImportError:
        print(f'{colorama.Fore.RED}Error: Required local modules not found.')
        print(f'Make sure filmow_scraper.py and media_sorter.py are in the same directory.{colorama.Style.RESET_ALL}')
        sys.exit(1)

    return FilmowScraper, MediaSorter


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='Extract and export your Filmow.com media collections',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '--username',
        '-u',
        type=str,
        help='Filmow username (if not provided, will prompt)'
    )

    parser.add_argument(
        '--output-dir',
        '-o',
        type=str,
        default='output',
        help='Directory for output files'
    )

    parser.add_argument(
        '--formats',
        '-f',
        type=str,
        default='all',
        choices=[
            'json',
            'xlsx',
            'csv',
            'all'
        ],
        help='Output formats to generate'
    )

    parser.add_argument(
        '--sort',
        '-s',
        type=str,
        default='title',
        choices=[
            'title',
            'rating',
            'favorite',
            'none'
        ],
        help='Primary sorting criterion'
    )

    parser.add_argument(
        '--movies-only',
        action='store_true',
        help='Only scrape movies, skip TV shows'
    )

    parser.add_argument(
        '--tv-only',
        action='store_true',
        help='Only scrape TV shows, skip movies'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=[
            'DEBUG',
            'INFO',
            'WARNING',
            'ERROR'
        ],
        help='Set the logging level'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Number of concurrent worker threads'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Request timeout in seconds'
    )

    parser.add_argument(
        '--language',
        '-l',
        type=str,
        default='pt',
        choices=[
            'pt',
            'en'
        ],
        help='Interface language (Portuguese or English)'
    )

    return parser.parse_args()


def get_translations(language: str) -> Dict[str, str]:
    """
    Get translations for the specified language.

    Args:
        language: Language code ('pt' or 'en')

    Returns:
        Dictionary of translated strings
    """
    translations = {
        'pt': {
            "welcome": 'Bem-vindo, {}. Vamos extrair os seus dados do Filmow.',
            "wait_message": 'Aguarde até a mensagem de conclusão do procedimento.\n',
            "username_prompt": 'Por favor, informe seu nome de usuário do Filmow: ',
            "extracting_movies": 'Extraindo filmes...',
            "extracting_tv": 'Extraindo séries...',
            "sorting_data": 'Ordenando dados...',
            "exporting_data": 'Exportando dados...',
            "json_success": 'Arquivo JSON "{}" criado com sucesso!',
            "excel_success": 'Arquivo Excel "{}" criado com sucesso!',
            "csv_success": 'Arquivos CSV criados com sucesso no diretório "{}"!',
            "completion": 'Procedimento concluído com sucesso!',
            "found_movies": 'Encontrados {} filmes assistidos, {} filmes favoritos e {} filmes para assistir.',
            "found_tv": 'Encontradas {} séries assistidas, {} séries favoritas e {} séries para assistir.',
            "movies_watched": 'Filmes - Já vi',
            "movies_favorites": 'Filmes - Favoritos',
            "movies_to_watch": 'Filmes - Quero ver',
            "tv_watched": 'Séries - Já vi',
            "tv_favorites": 'Séries - Favoritos',
            "tv_to_watch": 'Séries - Quero ver',
        },
        'en': {
            "welcome": 'Welcome, {}. Let\'s extract your data from Filmow.',
            "wait_message": 'Please wait until the completion message.\n',
            "username_prompt": 'Please enter your Filmow username: ',
            "extracting_movies": 'Extracting movies...',
            "extracting_tv": 'Extracting TV shows...',
            "sorting_data": 'Sorting data...',
            "exporting_data": 'Exporting data...',
            "json_success": 'JSON file "{}" created successfully!',
            "excel_success": 'Excel file "{}" created successfully!',
            "csv_success": 'CSV files created successfully in directory "{}"!',
            "completion": 'Process completed successfully!',
            "found_movies": 'Found {} watched movies, {} favorite movies, and {} movies to watch.',
            "found_tv": 'Found {} watched TV shows, {} favorite TV shows, and {} TV shows to watch.',
            "movies_watched": 'Movies - Watched',
            "movies_favorites": 'Movies - Favorites',
            "movies_to_watch": 'Movies - To Watch',
            "tv_watched": 'TV Shows - Watched',
            "tv_favorites": 'TV Shows - Favorites',
            "tv_to_watch": 'TV Shows - To Watch',
        }
    }

    return translations.get(
        language,
        translations['pt']
    )


def export_to_json(data: Dict[str, List[Dict[str, Any]]], filename: str, logger: logging.Logger) -> None:
    """
    Export data to a JSON file.

    Args:
        data: Dictionary of data to export
        filename: Output filename
        logger: Logger instance
    """
    try:
        with open(filename, 'w', encoding='utf-8') as outfile:
            json.dump(
                data,
                outfile,
                indent=4,
                ensure_ascii=False
            )
        logger.info(f'JSON data exported to {filename}')
    except Exception as e:
        logger.error(f'Error exporting to JSON: {str(e)}')


def export_to_excel(data: Dict[str, List[Dict[str, Any]]], filename: str, logger: logging.Logger) -> None:
    """
    Export data to an Excel file.

    Args:
        data: Dictionary of data to export
        filename: Output filename
        logger: Logger instance
    """
    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for sheet_name, data_list in data.items():
                if data_list:
                    df = pd.DataFrame(data_list)
                    df.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        index=False
                    )
        logger.info(f'Excel data exported to {filename}')
    except Exception as e:
        logger.error(f'Error exporting to Excel: {str(e)}')


def export_to_csv(data: Dict[str, List[Dict[str, Any]]], directory: str, logger: logging.Logger) -> None:
    """
    Export data to CSV files in the specified directory.

    Args:
        data: Dictionary of data to export
        directory: Output directory
        logger: Logger instance
    """
    try:
        os.makedirs(
            directory,
            exist_ok=True
        )

        for sheet_name, data_list in data.items():
            if data_list:
                # Create a safe filename
                safe_name = sheet_name.replace(
                    ' - ',
                    '_'
                ).replace(
                    ' ',
                    '_'
                ).lower()
                filename = os.path.join(
                    directory,
                    f'{safe_name}.csv'
                )

                df = pd.DataFrame(data_list)
                df.to_csv(
                    filename,
                    index=False,
                    encoding='utf-8-sig'
                )
                logger.debug(f'CSV data exported to {filename}')

        logger.info(f'All CSV files exported to {directory}')
    except Exception as e:
        logger.error(f'Error exporting to CSV: {str(e)}')


def create_output_directory(directory: str) -> None:
    """
    Create the output directory if it doesn't exist.

    Args:
        directory: Directory path to create
    """
    os.makedirs(
        directory,
        exist_ok=True
    )


def format_collection_data(
        movies_watched: List[Dict[str, Any]],
        movies_favorites: List[Dict[str, Any]],
        movies_to_watch: List[Dict[str, Any]],
        series_watched: List[Dict[str, Any]],
        series_favorites: List[Dict[str, Any]],
        series_to_watch: List[Dict[str, Any]],
        i18n: Dict[str, str]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Format collection data for export.

    Args:
        movies_*: Movie collection lists
        series_*: TV show collection lists
        i18n: Translations dictionary

    Returns:
        Formatted data dictionary
    """
    return {
        i18n['movies_watched']: movies_watched,
        i18n['movies_favorites']: movies_favorites,
        i18n['movies_to_watch']: movies_to_watch,
        i18n['tv_watched']: series_watched,
        i18n['tv_favorites']: series_favorites,
        i18n['tv_to_watch']: series_to_watch,
    }


def print_colored(message: str, color: str, logger: logging.Logger) -> None:
    """
    Print a colored message to the console and log it.

    Args:
        message: Message to print
        color: Color to use (from colorama.Fore)
        logger: Logger instance
    """
    colorama_colors = {
        'red': colorama.Fore.RED,
        'green': colorama.Fore.GREEN,
        'yellow': colorama.Fore.YELLOW,
        'blue': colorama.Fore.BLUE,
        'magenta': colorama.Fore.MAGENTA,
        'cyan': colorama.Fore.CYAN,
        'white': colorama.Fore.WHITE,
    }

    color_code = colorama_colors.get(
        color.lower(),
        colorama.Fore.WHITE
    )
    print(f'{color_code}{message}{colorama.Style.RESET_ALL}')
    logger.info(message)


def main():
    """Main function to run the Filmow exporter."""
    check_and_install_dependencies()

    # Parse command line arguments
    args = parse_arguments()

    logger = setup_logger(args.log_level)
    logger.debug(f'Arguments: {args}')

    FilmowScraper, MediaSorter = import_dependencies()

    i18n = get_translations(args.language)

    username = args.username
    if not username:
        username = input(i18n['username_prompt'])

    print_colored(
        i18n['welcome'].format(username),
        'green',
        logger
    )
    print(i18n['wait_message'])

    create_output_directory(args.output_dir)

    scraper = FilmowScraper(
        username,
        max_workers=args.workers,
        timeout=args.timeout
    )
    sorter = MediaSorter()

    movies_watched, movies_favorites, movies_to_watch = [], [], []
    series_watched, series_favorites, series_to_watch = [], [], []

    try:
        if not args.tv_only:
            print_colored(
                i18n['extracting_movies'],
                'cyan',
                logger
            )
            movies_watched, movies_favorites, movies_to_watch = scraper.get_media(FilmowScraper.MOVIES)
            print_colored(
                i18n['found_movies'].format(
                    len(movies_watched),
                    len(movies_favorites),
                    len(movies_to_watch)
                ),
                'blue',
                logger
            )

        if not args.movies_only:
            print_colored(
                i18n['extracting_tv'],
                'cyan',
                logger
            )
            series_watched, series_favorites, series_to_watch = scraper.get_media(FilmowScraper.TV_SHOWS)
            print_colored(
                i18n['found_tv'].format(
                    len(series_watched),
                    len(series_favorites),
                    len(series_to_watch)
                ),
                'blue',
                logger
            )

        print_colored(
            i18n['sorting_data'],
            'cyan',
            logger
        )

        collections = [
            movies_watched,
            movies_favorites,
            movies_to_watch,
            series_watched,
            series_favorites,
            series_to_watch,
        ]

        if args.sort == 'title':
            collections = [sorter.sort_by_title(collection) for collection in collections]
        elif args.sort == 'rating':
            # Sort watched and favorites by rating
            for i in [0, 1, 3, 4]:  # Indices for watched and favorites lists
                if i < len(collections) and collections[i]:
                    collections[i] = sorter.sort_by_rating(collections[i])
            # Sort to-watch lists alphabetically
            for i in [2, 5]:  # Indices for to-watch lists
                if i < len(collections) and collections[i]:
                    collections[i] = sorter.sort_by_title(collections[i])
        elif args.sort == 'favorite':
            # Apply favorite sorting to watched lists
            for i in [0, 3]:  # Indices for watched lists
                if i < len(collections) and collections[i]:
                    collections[i] = sorter.sort_by_favorite(collections[i])
            # Sort other lists alphabetically
            for i in [1, 2, 4, 5]:  # Indices for other lists
                if i < len(collections) and collections[i]:
                    collections[i] = sorter.sort_by_title(collections[i])

        # Advanced sorting: favorite first, then rating, then title for watched lists
        if args.sort in ['rating', 'favorite']:
            for i in [0, 3]:  # Indices for watched lists
                if i < len(collections) and collections[i]:
                    collections[i] = sorter.sort_by_multiple_keys(
                        collections[i],
                        [
                        {
                            'key': 'Favorito',
                            'reverse': True,
                            'type': 'boolean'
                        },
                        {
                            'key': 'Nota do usuário',
                            'reverse': True,
                            'type': 'numeric'
                        },
                        {
                            'key': 'Título nacional',
                            'reverse': False,
                            'type': 'string'
                        }
                        ]
                    )

        # Unpack sorted collections
        [
            movies_watched,
            movies_favorites,
            movies_to_watch,
            series_watched,
            series_favorites,
            series_to_watch
        ] = collections

        # Format data for export
        filmow_data = format_collection_data(
            movies_watched,
            movies_favorites,
            movies_to_watch,
            series_watched,
            series_favorites,
            series_to_watch,
            i18n
        )

        # Export data in requested formats
        print_colored(
            i18n['exporting_data'],
            'cyan',
            logger
        )
        formats = args.formats.lower().split(',') if ',' in args.formats else [args.formats.lower()]
        if 'all' in formats:
            formats = [
                'json',
                'xlsx',
                'csv'
            ]

        # Generate filenames
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        base_filename = f'filmow_{username}_{timestamp}'
        json_filename = os.path.join(
            args.output_dir,
            f'{base_filename}.json'
        )
        excel_filename = os.path.join(
            args.output_dir,
            f'{base_filename}.xlsx'
        )
        csv_directory = os.path.join(
            args.output_dir,
            f'{base_filename}_csv'
        )

        # Export in each requested format
        if 'json' in formats:
            export_to_json(
                filmow_data,
                json_filename,
                logger
            )
            print_colored(
                i18n['json_success'].format(json_filename),
                'green',
                logger
            )

        if 'xlsx' in formats:
            export_to_excel(
                filmow_data,
                excel_filename,
                logger
            )
            print_colored(
                i18n['excel_success'].format(excel_filename),
                'green',
                logger
            )

        if 'csv' in formats:
            export_to_csv(
                filmow_data,
                csv_directory,
                logger
            )
            print_colored(
                i18n['csv_success'].format(csv_directory),
                'green',
                logger
            )

        # Print completion message
        print_colored(
            i18n['completion'],
            'green',
            logger
        )

    except Exception as e:
        logger.error(
            f'Error during execution: {str(e)}',
            exc_info=True
        )
        print_colored(
            f'Error: {str(e)}',
            'red',
            logger
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
