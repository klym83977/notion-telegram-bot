import requests
from datetime import date
from config import NOTION_TOKEN, NOTION_DATABASE_ID, NOTION_NOTES_DATABASE_ID, NOTION_VERSION

def create_notion_task(task_text, status, priority, tag, deadline_iso=None, image_url=None):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": task_text}}]},
            "Status": {"status": {"name": status}},
            "Priority": {"select": {"name": priority}},
            "Tags": {"multi_select": [{"name": tag}]}
        }
    }
    if deadline_iso: 
        data["properties"]["Deadline"] = {"date": {"start": deadline_iso}}
        
    if image_url:
        data["children"] = [{"object": "block", "type": "image", "image": {"type": "external", "external": {"url": image_url}}}]
        
    try:
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200, response.text if response.status_code != 200 else "OK"
    except Exception as e:
        return False, str(e)

def create_notion_note(note_text, tag, image_url=None):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    
    data = {
        "parent": {"database_id": NOTION_NOTES_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": note_text}}]}
        }
    }
    
    if tag:
        data["properties"]["Tags"] = {"multi_select": [{"name": tag}]}
        
    if image_url:
        data["children"] = [{"object": "block", "type": "image", "image": {"type": "external", "external": {"url": image_url}}}]
        
    try:
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200, response.text if response.status_code != 200 else "OK"
    except Exception as e:
        return False, str(e)

def get_todays_tasks():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    
    today_iso = date.today().strftime("%Y-%m-%d")
    
    query_data = {
        "filter": {
            "and": [
                {"property": "Status", "status": {"does_not_equal": "Готово"}},
                {"or": [
                    {"property": "Deadline", "date": {"equals": today_iso}},
                    {"property": "Status", "status": {"equals": "В процесі"}}
                ]}
            ]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=query_data)
        return response.status_code == 200, response.json() if response.status_code == 200 else response.text
    except Exception as e:
        return False, str(e)
