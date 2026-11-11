# MailCanvas Android

A small Android WebView app for the hosted MailCanvas HTML email studio.

## Build APK
1. Open the **Actions** tab.
2. Select **Build MailCanvas APK**.
3. Press **Run workflow** (or wait for the push-triggered build).
4. Open the completed workflow run and download the **MailCanvas-debug-apk** artifact.
5. Extract the ZIP to get `app-debug.apk`.

The app loads the hosted MailCanvas website. The Resend API key must remain on the Vercel server as an environment variable; never put it in this Android project or APK.
