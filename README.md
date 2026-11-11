# Tom Kids World

A free-first YouTube Kids video workflow for the **Tom Kids World** channel.

## Current starter setup

- GitHub Actions runs on demand.
- Python creates a narrated slideshow video from an original story in `content/story.txt`.
- Microsoft Edge neural TTS is used through the community `edge-tts` package (free service; availability and terms can change).
- FFmpeg renders the MP4.
- YouTube upload uses the official YouTube Data API and OAuth refresh-token credentials.
- Upload metadata sets `selfDeclaredMadeForKids: true`.

This starter does **not** generate original 3D animation or guarantee 5–10 minute videos. The story should be original and long enough for the intended runtime. Review every video before publishing.

## Required GitHub Actions secret

Create a repository secret named `YOUTUBE_TOKEN_JSON`. Its value must be the complete JSON contents of an authorized Google OAuth user-token file that includes a refresh token and belongs to the YouTube channel owner. Do not paste credentials into chat or commit them to this repository.

The downloaded Google Cloud OAuth **client** JSON alone is not a user token and is not enough to upload. The OAuth consent screen must be configured, and the Google account used for authorization must own or manage the Tom Kids World channel.

## Run

1. Replace `content/story.txt` with an original, age-appropriate English story.
2. Open **Actions** → **Build and upload Tom Kids World video**.
3. Select **Run workflow**, enter the title and description, then choose visibility.
4. Check the generated video and YouTube Studio after the run.

For the first test, use **private** visibility. Once the workflow and channel settings are verified, you can choose public.

## Important

- This is a starter workflow, not unlimited AI video generation.
- The first version uses illustrated title cards/slides, not full 3D cartoon animation.
- Keep all OAuth credentials in GitHub Secrets.
- Marking videos as Made for Kids disables or limits some YouTube features and personalized advertising.
- Follow YouTube's child-safety, quality, copyright, and monetization policies.
