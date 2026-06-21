"""Quick script to check latest presentation sessions in Supabase."""
import json
import sys
sys.path.insert(0, ".")

from app.integrations.supabase_client import get_supabase_client

client = get_supabase_client()

# Get latest presentation sessions
result = (
    client.table("sessions")
    .select("*")
    .eq("session_type", "presentation")
    .order("created_at", desc=True)
    .limit(5)
    .execute()
)

print(f"Found {len(result.data)} presentation sessions:\n")
for s in result.data:
    session_id = s["id"]
    print(f"--- Session: {session_id} ---")
    print(f"  Status: {s['status']}")
    print(f"  Title/Role: {s.get('role', 'N/A')}")
    print(f"  Topic: {s.get('topic', 'N/A')}")
    print(f"  Overall Score: {s.get('overall_score', 'N/A')}")
    print(f"  Communication Score: {s.get('communication_score', 'N/A')}")
    print(f"  Duration (sec): {s.get('duration_seconds', 'N/A')}")
    print(f"  Created: {s.get('created_at', 'N/A')}")
    print(f"  Completed: {s.get('completed_at', 'N/A')}")
    print()

# Check feedback for any completed session
completed = [s for s in result.data if s["status"] == "completed"]
if completed:
    sid = completed[0]["id"]
    fb = client.table("session_feedback").select("*").eq("session_id", sid).execute()
    if fb.data:
        print(f"--- Feedback for {sid} ---")
        f = fb.data[0]
        print(f"  Strengths: {json.dumps(f.get('strengths', []), indent=4)}")
        print(f"  Weaknesses: {json.dumps(f.get('weaknesses', []), indent=4)}")
        print(f"  Recommendations: {json.dumps(f.get('recommendations', []), indent=4)}")
        scores = f.get("presentation_scores")
        if scores:
            print(f"  Presentation Scores: {json.dumps(scores, indent=4)}")
    else:
        print(f"No feedback found for session {sid}")
else:
    print("No completed presentation sessions found.")

# Check storage buckets
print("\n--- Storage Buckets ---")
try:
    buckets = client.storage.list_buckets()
    for b in buckets:
        print(f"  Bucket: {b.name}")
except Exception as e:
    print(f"  Error listing buckets: {e}")
