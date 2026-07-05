from django import template

register = template.Library()

@register.filter
def initials(value):
    """Return initials (first letters of words) up to 2."""
    if not value:
        return "?"
    parts = value.strip().split()
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()

@register.filter
def avatar_style(value):
    """Return a CSS background gradient based on the name."""
    colors = [
        ('#6B1E3C','#C9972E'),
        ('#8A2A4E','#E8C170'),
        ('#45142A','#C9972E'),
        ('#7A2348','#D4A85B'),
        ('#5C1832','#CBA24B'),
        ('#6B1E3C','#B98A3A')
    ]
    idx = sum(ord(c) for c in value) % len(colors)
    c1, c2 = colors[idx]
    return f'background: linear-gradient(135deg, {c1}, {c2});'