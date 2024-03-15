from django.shortcuts import render

# Create your views here.
def feedView(request):
    feed_items = [
        {"user": "John Doe", "content": "Random", "timestamp": "2024-03-14 10:00:00"},
        {"user": "Jane Smith", "content": "Super Random", "timestamp": "2024-03-14 11:00:00"},
        {"user": "Alice Johnson", "content": "Ultra Random", "timestamp": "2024-03-14 12:00:00"}
    ]

feed_html = "<h1>Feed</h1>"
for item in feed_items:
        feed_html += f"<div><p>User: {item['user']}</p>"
        feed_html += f"<p>Content: {item['content']}</p>"
        feed_html += f"<p>Timestamp: {item['timestamp']}</p></div>"

return HttpResponse(feed_html)