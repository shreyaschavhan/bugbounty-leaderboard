import csv
import requests
from datetime import datetime, timedelta
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import hashlib
import json
import shutil
import logging
import sys

# Configuration
CSV_URL = "https://docs.google.com/spreadsheets/d/13e3IkEEu7L_pQZP30hVxLnE9byW4HPWnLjoZyG6BSy8/export?format=csv&gid=120863043"
TODAY = datetime.now()
SEVEN_DAYS_AGO = TODAY - timedelta(days=7)
CACHE_VERSION = "v1.1"  # Incremented for new battle of selves logic

# Cache file path
CACHE_FILE = Path('user_cache.json')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_cache():
    """Load the cache file if it exists and is valid JSON."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error("Cache file is corrupted. Starting with empty cache.")
            return {}
    return {}

def save_cache(cache):
    """Save the cache to file with error handling."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except IOError as e:
        logger.error(f"Failed to save cache: {e}")

def fetch_csv_data(url):
    """Fetch CSV data from the given URL with retry logic and error handling."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt == max_retries - 1:
                logger.error(f"Failed to fetch CSV data from {url} after {max_retries} attempts")
                sys.exit(1)
            # Wait before retrying
            import time
            time.sleep(2 ** attempt)  # Exponential backoff

def parse_csv_data(csv_text):
    """Parse CSV data with validation for required columns and data types."""
    data = csv_text.splitlines()
    try:
        reader = csv.DictReader(data)
    except csv.Error as e:
        logger.error(f"CSV parsing failed: {e}")
        sys.exit(1)
    
    required_columns = ['Timestamp', 'Handle', 'Score', 'Deep_Action_Summary']
    if not reader.fieldnames or not all(col in reader.fieldnames for col in required_columns):
        logger.error(f"CSV missing required columns. Expected: {required_columns}, found: {reader.fieldnames}")
        sys.exit(1)
    
    user_scores = {}
    recent_actions = []
    user_actions = {}
    
    for row_num, row in enumerate(reader, start=2):  # row_num includes header row
        timestamp_str = row['Timestamp']
        try:
            timestamp = datetime.strptime(timestamp_str, '%d/%m/%Y %H:%M:%S')
        except ValueError:
            logger.warning(f"Row {row_num}: Invalid timestamp format '{timestamp_str}'. Skipping.")
            continue
        
        if timestamp < SEVEN_DAYS_AGO:
            continue
        
        name = row['Handle'].strip()
        if not name:
            logger.warning(f"Row {row_num}: Missing user name. Skipping.")
            continue
        
        try:
            score = float(row['Score'])
        except ValueError:
            logger.warning(f"Row {row_num}: Invalid score '{row['Score']}' for user '{name}'. Skipping.")
            continue
        
        summary = row['Deep_Action_Summary'].strip()
        
        # Update user scores and actions
        user_scores[name] = user_scores.get(name, 0.0) + score
        action_entry = {
            'timestamp': timestamp,
            'score': score,
            'summary': summary
        }
        recent_actions.append({
            'name': name,
            **action_entry
        })
        if name not in user_actions:
            user_actions[name] = []
        user_actions[name].append(action_entry)
    
    return user_scores, recent_actions, user_actions

def generate_cache_key(user_data, templates_dir='templates'):
    """Generate a cache key that incorporates user data, template hashes, and script version."""
    # Hash the user data
    user_data_str = json.dumps(user_data, sort_keys=True, default=str)
    data_hash = hashlib.md5(user_data_str.encode()).hexdigest()
    
    # Hash all template files to detect changes
    template_hashes = []
    try:
        for template_file in Path(templates_dir).glob('*.html'):
            with open(template_file, 'rb') as f:
                content = f.read()
                template_hash = hashlib.md5(content).hexdigest()
                template_hashes.append(template_hash)
    except FileNotFoundError:
        logger.error(f"Templates directory '{templates_dir}' not found.")
        sys.exit(1)
    
    # Sort hashes to ensure consistent order
    template_hashes.sort()
    templates_hash = hashlib.md5(''.join(template_hashes).encode()).hexdigest()
    
    # Combine with cache version for logic changes
    combined = f"{data_hash}_{templates_hash}_{CACHE_VERSION}"
    return hashlib.md5(combined.encode()).hexdigest()

def copy_static_files(target_static_dir):
    """Copy static files to the target static directory with error handling."""
    static_files = {
        'css': Path('static/css/style.css'),
        'js': Path('static/js/script.js')
    }
    for file_type, src_path in static_files.items():
        if not src_path.exists():
            logger.error(f"Static file not found: {src_path}")
            sys.exit(1)
        try:
            destination_subdir = target_static_dir / file_type
            destination_subdir.mkdir(parents=True, exist_ok=True)
            dest_path = destination_subdir / src_path.name

            # Skip if source and destination are the same file
            if src_path.resolve() == dest_path.resolve():
                logger.info(f"Skipping copy for {src_path} (source and destination are the same)")
                continue

            shutil.copy2(src_path, dest_path)
        except (shutil.Error, OSError) as e:
            if "being used by another process" in str(e):
                logger.warning(f"File {src_path} is locked by another process. Skipping copy.")
            else:
                logger.error(f"Failed to copy {src_path}: {e}")
                sys.exit(1)

def calculate_battle_of_selves(user_actions, user_name):
    """Calculate Past Self, Present Self, and Future Self metrics."""
    # Get actions from the last 7 days
    seven_days_ago = TODAY - timedelta(days=7)
    recent_actions = [a for a in user_actions if a['timestamp'] >= seven_days_ago]
    
    # Group actions by day
    daily_scores = {}
    for action in recent_actions:
        date_str = action['timestamp'].strftime('%Y-%m-%d')
        daily_scores[date_str] = daily_scores.get(date_str, 0) + action['score']
    
    # Calculate Past Self (7-day average)
    past_self_avg = sum(daily_scores.values()) / 7 if daily_scores else 0
    
    # Calculate Present Self (today's score)
    today_str = TODAY.strftime('%Y-%m-%d')
    present_self_score = daily_scores.get(today_str, 0)
    
    # Calculate Future Self (tomorrow's goal - 10% more than average)
    future_self_projection = past_self_avg * 1.1
    
    return past_self_avg, present_self_score, future_self_projection

def main():
    logger.info("Starting build process...")
    
    # Load existing cache
    user_cache = load_cache()
    new_cache = {}
    
    # Fetch and parse CSV data
    csv_text = fetch_csv_data(CSV_URL)
    user_scores, recent_actions, user_actions = parse_csv_data(csv_text)
    
    # Sort users by score descending
    sorted_users = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    sorted_users_with_rank = list(enumerate(sorted_users, start=1))
    
    # Sort recent actions by timestamp
    recent_actions.sort(key=lambda x: x['timestamp'], reverse=True)
    top_recent_actions = recent_actions[:10]
    
    # Set up Jinja2 environment
    templates_dir = 'templates'
    env = Environment(loader=FileSystemLoader(templates_dir))
    
    # Define and create output directories
    users_dir = Path('users')
    output_static_dir = Path('static') # Destination for static files
    try:
        users_dir.mkdir(exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create directory {users_dir}: {e}")
        sys.exit(1)

    # Copy static files
    copy_static_files(output_static_dir)
    
    # Render main leaderboard page
    leaderboard_template = env.get_template('leaderboard.html')
    leaderboard_context = {
        'sorted_users': sorted_users_with_rank,
        'user_actions': user_actions,
        'top_recent_actions': top_recent_actions,
        'SEVEN_DAYS_AGO': SEVEN_DAYS_AGO,
        'TODAY': TODAY
    }
    try:
        index_html = leaderboard_template.render(**leaderboard_context)
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(index_html)
        logger.info("Rendered leaderboard page to index.html.")
    except Exception as e:
        logger.error(f"Failed to render leaderboard: {e}")
        sys.exit(1)
    
    # Render user dashboards with enhanced caching
    for name, score in user_scores.items():
        user_data = user_actions.get(name, [])
        cache_key = generate_cache_key(user_data, templates_dir)
        
        # Check cache for existing valid entry
        if name in user_cache and user_cache[name] == cache_key:
            new_cache[name] = cache_key
            logger.info(f"Cache hit for user '{name}'. Skipping dashboard generation.")
            continue
        
        # Find user rank
        try:
            user_rank = next(rank for rank, (n, s) in sorted_users_with_rank if n == name)
        except StopIteration:
            logger.warning(f"User '{name}' not found in sorted list. Skipping dashboard.")
            continue
        
        # Calculate streak: consecutive days with actions up to today
        dates_with_actions = {action['timestamp'].date() for action in user_data}
        streak = 0
        current_date = TODAY.date()
        while current_date >= SEVEN_DAYS_AGO.date():
            if current_date in dates_with_actions:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        # Calculate Battle of Selves metrics
        past_self_avg, present_self_score, future_self_projection = calculate_battle_of_selves(user_data, name)
        
        # Calculate actual chart data
        current_week_scores = [0] * 7
        previous_week_scores = [0] * 7
        
        # Calculate scores for each day of current week
        for action in user_data:
            days_ago = (TODAY.date() - action['timestamp'].date()).days
            if 0 <= days_ago < 7:
                current_week_scores[6 - days_ago] += action['score']
        
        # Render user dashboard
        dashboard_template = env.get_template('user_dashboard.html')
        dashboard_context = {
            'user_name': name,
            'user_score': score,
            'user_rank': user_rank,
            'user_actions': user_data,
            'streak': streak,
            'TODAY': TODAY,
            'SEVEN_DAYS_AGO': SEVEN_DAYS_AGO,
            'days': [(TODAY - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)],
            'current_week_scores': current_week_scores,
            'previous_week_scores': previous_week_scores,
            'past_self_avg': round(past_self_avg, 1),
            'present_self_score': round(present_self_score, 1),
            'future_self_projection': round(future_self_projection, 1),
            'relative_path': '../'  # This will help with relative paths in user pages
        }
        try:
            user_html = dashboard_template.render(**dashboard_context)
            user_filename = f"user_{name.lower().replace(' ', '_')}.html"
            with open(users_dir / user_filename, 'w', encoding='utf-8') as f:
                f.write(user_html)
            new_cache[name] = cache_key
            logger.info(f"Rendered dashboard for user '{name}' in '{users_dir}/' directory.")
        except Exception as e:
            logger.error(f"Failed to render dashboard for user '{name}': {e}")
    
    # Save the new cache
    save_cache(new_cache)
    logger.info("Build complete. index.html is in the main directory and user dashboards are in the 'users/' directory.")
    
if __name__ == '__main__':
    main()