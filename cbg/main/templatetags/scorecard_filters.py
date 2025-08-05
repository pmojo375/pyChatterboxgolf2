from django import template

register = template.Library()

@register.filter
def index(list_obj, index):
    """
    Returns the item at the specified index from a list
    """
    try:
        return list_obj[index]
    except (IndexError, TypeError):
        return ""

@register.filter
def score_class(score_data):
    """
    Returns CSS class for score color coding
    score_data should be a tuple: (score, par)
    """
    score, par = score_data
    if score == 0:
        return ""
    
    relative_to_par = score - par
    
    if relative_to_par <= -2:
        return "score-eagle"
    elif relative_to_par == -1:
        return "score-birdie"
    elif relative_to_par == 0:
        return "score-par"
    elif relative_to_par == 1:
        return "score-bogey"
    elif relative_to_par == 2:
        return "score-double"
    elif relative_to_par == 3:
        return "score-triple"
    else:
        return "score-worse"

@register.filter
def stroke_class(strokes):
    """
    Returns CSS class for stroke borders
    """
    if strokes >= 3:
        return "stroke-3"
    elif strokes == 2:
        return "stroke-2"
    elif strokes == 1:
        return "stroke-1"
    else:
        return "" 

@register.filter
def get_item(dictionary, key):
    """Template filter to get dictionary item by key"""
    return dictionary.get(key) 

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divide the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def format_date_string(date_string):
    """Format a date string (YYYY-MM-DD) to a readable format"""
    try:
        from datetime import datetime
        from django.utils import timezone
        # Parse as naive datetime first
        naive_date = datetime.strptime(date_string, '%Y-%m-%d')
        # Make it timezone-aware in the current timezone
        date_obj = timezone.make_aware(naive_date)
        return date_obj.strftime('%A, %B %d')
    except (ValueError, TypeError):
        return date_string 