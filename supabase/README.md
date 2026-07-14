# Dream Board Supabase setup

1. Create a Supabase project.
2. In **Authentication → Providers**, enable **Anonymous Sign-Ins**.
3. Open the SQL Editor and run [`schema.sql`](./schema.sql).
4. In the project's API settings, copy the **Project URL** and **Publishable key** into `assets/hope-config.js`.
5. Do not use the `service_role` key in the website.

The schema exposes only four narrowly scoped database functions to visitors:

- `get_dream_board_posts`
- `create_dream_board_post`
- `toggle_dream_board_reaction`
- `report_dream_board_post`

The underlying tables cannot be accessed directly by anonymous visitors. Posts and reports are rate-limited in the database, and Spotify embed URLs are reconstructed server-side from validated song, album, or playlist IDs.

The schema intentionally contains no demo or seed posts, so a new installation starts with an empty board.
