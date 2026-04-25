import { SubredditSetupPanel } from "@/components/subreddit-setup-panel";
import { listLiveSubreddits } from "@/lib/live-api";

export const dynamic = "force-dynamic";

export default async function SubredditSetupPage() {
  const subreddits = await listLiveSubreddits();

  return (
    <div className="mx-auto max-w-6xl">
      <SubredditSetupPanel initialSubreddits={subreddits} />
    </div>
  );
}
