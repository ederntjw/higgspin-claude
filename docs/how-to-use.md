# How to use higgspin-claude

A walkthrough for people who have never touched code, AI image tools, or a terminal before. If you can copy and paste, you can do this. The whole thing takes about 15 minutes the first time, and 30 seconds every time after.

---

## What you'll have at the end

A finished 10-second vertical video ad — the kind that fits TikTok, Reels, and Shorts — built from a handful of inspiration images you picked. Optionally, with your real product locked into every frame so the AI doesn't invent a fake bottle or rewrite your label.

You don't write any prompts. You don't pick any AI models. You don't open Photoshop or Premiere. You have a conversation with an AI assistant called **Claude**, and Claude does the work.

---

## The whole flow in three steps

```
  1. Download the project          2. Open it in a code editor          3. Talk to Claude
       (one command)                 (VSCode, Antigravity, Cursor)         ("how do I use this?")
```

That's the entire user experience. Everything else — installing things, picking AI models, generating images, stitching the video — is something Claude walks you through, conversationally, after step 3.

---

## What you need before you start

Three things. All free to try:

1. **A computer running macOS or Linux.** Windows works too via WSL, but the instructions below are for Mac and Linux.
2. **A Higgsfield account.** This is the AI service that actually generates your images and video. Sign up at [higgsfield.ai](https://higgsfield.ai). Their pricing is credit-based; a 10-second ad uses a small handful of credits.
3. **A Pinterest account.** We use Pinterest as a fresh visual source — based on your moodboard, the project searches Pinterest for 40 more matching images so we have variety to draw from. You probably already have one.

Optionally — but strongly recommended:

- **A clean photo of your product.** White or transparent background, sharp focus, even lighting. If you give us this, the AI keeps the *exact* product visible in every frame. Without it, the AI generates editorial scenes in your style that you can composite a real product into later.

---

## Step 1 — Download the project

Open your computer's **Terminal** app (it's pre-installed; on Mac you can find it via Spotlight: ⌘+Space, type "Terminal", hit enter).

Paste this and hit enter:

```bash
git clone https://github.com/ederntjw/higgspin-claude
cd higgspin-claude
```

This downloads the project into a folder called `higgspin-claude` and moves you into it. If your computer asks you to install developer tools (Xcode Command Line Tools on Mac), say yes — it's a one-time, free, official Apple install.

Now run the setup script:

```bash
./setup.sh
```

This installs the Python libraries the project needs. Everything goes inside the project folder (in a hidden subfolder called `.venv`), so nothing on the rest of your computer is affected. If the script tells you `ffmpeg` is missing, install it:

- **Mac:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

`ffmpeg` is the tool that combines video clips and audio together — it's what produces your final stitched ad.

---

## Step 2 — Open the project in a code editor

You don't need to know how to code. You're using the editor as a place where you can chat with Claude *and* have it look at the project files at the same time. Pick whichever editor you prefer:

| Editor | Why pick this | Get it |
|---|---|---|
| **VS Code** | The most popular, most documented option. Free. Works everywhere. | [code.visualstudio.com](https://code.visualstudio.com) |
| **Antigravity** | Google's newer agentic IDE; built around AI assistants. Free. | [antigravity.google](https://antigravity.google) |
| **Cursor** | A fork of VS Code with AI built in. Free tier available. | [cursor.com](https://cursor.com) |

Once installed, **open the `higgspin-claude` folder** you just downloaded:

- VS Code / Cursor / Antigravity → **File** → **Open Folder…** → pick `higgspin-claude`.

You should see the project's files listed in a sidebar on the left.

---

## Step 3 — Install Claude Code and ask it to start

**Claude Code** is the AI assistant that runs the project for you. Install it:

```bash
npm install -g @anthropic-ai/claude-code
```

(If `npm` isn't on your computer yet, install [Node.js](https://nodejs.org) first — it ships with `npm`.)

Now, inside your code editor, open the **integrated terminal**:

- **VS Code / Cursor:** **View** → **Terminal** (or press <kbd>Ctrl</kbd>+<kbd>`</kbd>).
- **Antigravity:** built-in chat is already open; you can use that or open a terminal panel.

In that terminal, type:

```bash
claude
```

A chat panel opens. Now just say to Claude, in plain English:

> *"How do I use this?"*
>
> *"I want to make an ad — help me get started."*
>
> *"First time here, walk me through it."*

Any of these works. Claude reads the project's master instructions (a file called `CLAUDE.md` that lives in this repo) and takes over from there.

---

## What Claude does next

Claude walks you through the rest as a conversation. You don't run any more commands yourself. Claude will:

1. **Ask what you're advertising.** What's the product? Who's the audience? What feeling should the ad give?
2. **Ask for your moodboard.** Drop 5–10 inspiration images into a folder called `references/images/`. They don't need to be related to your actual product — they just need to capture the vibe.
3. **Ask if you have a product photo.** If yes, drop it at `references/product/hero.png` and the AI will lock that exact product into every frame.
4. **Check that everything's installed.** If anything's missing, Claude tells you what it is, why it's needed, and exactly what to paste to install it.
5. **Confirm before spending any credits.** You'll see a summary — topic, image count, ad length, expected credit usage — and Claude waits for your "yes" before running.
6. **Run the 8-stage pipeline.** Claude streams progress to you: reading your references, scraping Pinterest, generating images, building the storyboard, generating video clips, stitching with music. About 8–12 minutes end to end.
7. **Hand you the finished ad.** Your video lives at `output/ad/final.mp4`. Open it. Post it.

You can stop at any stage and ask Claude to redo something, swap a still, change the music, or run a longer 30-second version. Just say it in plain English.

---

## What it looks like in practice

A real first conversation with Claude looks like this:

> **You:** how do I use this?
>
> **Claude:** Welcome! Before we touch any code, I want to understand what you're making. A few quick questions:
> 1. What are you advertising?
> 2. Who's the audience?
> 3. What feeling should the ad give?
>
> **You:** A new sparkling water brand for young people. I want it to feel clean, fresh, a bit playful.
>
> **Claude:** Great. Now I need a moodboard — 5 to 10 images that capture that vibe. They don't need to be related to sparkling water; just images that feel right. Pinterest, Instagram screenshots, photos you took, frames from films you like — whatever. Drop them into `references/images/` and tell me when you're done…

…and from there it's just a chat. Claude does everything, and asks you for input whenever a creative decision needs to be made.

---

## Common questions

**Do I need to write prompts?**
No. Claude reads your reference images with its own vision and writes detailed prompts behind the scenes — including lighting, camera lens, film stock, photographer reference, composition. You just provide images and feedback.

**Do I need to know which AI model to use?**
No. The project auto-routes between Higgsfield's models (Nano-Banana-Pro, Flux Kontext, Soul Inpaint, Kling 2.1 Pro, Seedance 2 Fast) based on your moodboard's aesthetic. You can override it later if you become a power user, but you don't need to.

**Will my Pinterest password leave my computer?**
No. The project uses a real browser running locally on your machine to log in to Pinterest as you. Your credentials sit in a file called `.env` inside the project folder, which is on *your* computer. Nothing is sent to any third party. If you'd rather not save the password, you can manually log in once when the browser opens.

**How much will it cost?**
A 10-second ad uses a small handful of Higgsfield credits — exactly how many depends on which models the cascade picks for your specific aesthetic. The Higgsfield service itself doesn't currently return per-call cost in its responses, so the project can't estimate it for you up-front; instead, sign in to your [Higgsfield dashboard](https://higgsfield.ai) and watch live usage. New users get free credits to try with.

**Can I make a longer ad?**
Yes. Once you've done your first run, just say to Claude *"run a 30-second version"* and it does the rest. The default is 10 seconds (2 × 5-second clips); 30 seconds is 6 × 5-second clips.

**Can I redo just one part?**
Yes. *"Only redo the video"* or *"keep the images, swap the music"* both work. The project saves every intermediate result to disk, so it can resume from any point.

**What if something fails halfway through?**
Tell Claude what you saw and it'll diagnose and fix it. The most common first-run hiccup is a Pinterest CAPTCHA in the visible browser — you solve it once, the session is cached, future runs are smooth.

**Do I need to install or learn Photoshop / Premiere / DaVinci Resolve?**
No. The project produces a finished, ready-to-post `.mp4`. You can post it as-is, or if you want to tweak it later, the individual clips and stills are also saved to disk so you can drop them into any editor of your choice.

---

## When you're ready

Open Terminal, paste:

```bash
git clone https://github.com/ederntjw/higgspin-claude
cd higgspin-claude
./setup.sh
```

Open the folder in VS Code, Antigravity, or Cursor. Open the integrated terminal, run `claude`, and type:

> *"how do I use this?"*

That's it. Claude takes it from there.
