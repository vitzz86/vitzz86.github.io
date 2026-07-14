# Dream Board Supabase setup

1. Create a Supabase project.
2. In **Authentication → Providers**, enable **Anonymous Sign-Ins**.
3. Open the SQL Editor and run [`schema.sql`](./schema.sql), then [`youtube_upgrade.sql`](./youtube_upgrade.sql), and finally [`comments_upgrade.sql`](./comments_upgrade.sql).
4. In the project's API settings, copy the **Project URL** and **Publishable key** into `assets/hope-config.js`.
5. Do not use the `service_role` key in the website.

The schema exposes only narrowly scoped database functions to visitors:

- `get_dream_board_posts`
- `create_dream_board_post`
- `create_dream_board_post_v2`
- `toggle_dream_board_reaction`
- `get_dream_board_comments`
- `create_dream_board_comment`
- `report_dream_board_post`

The underlying tables cannot be accessed directly by anonymous visitors. Posts, comments, and reports are rate-limited in the database. Spotify and YouTube embed URLs are reconstructed server-side from validated item IDs, and each post can attach at most one media provider.

The schema intentionally contains no demo or seed posts, so a new installation starts with an empty board.
