# Training Environment for Healthcare AI

Hey, so here's what this folder is about, in plain English before we get into the weeds.

I want to eventually build cool stuff with healthcare data and AI. But here's the catch: real patient records are (rightfully) locked down tight. Hospitals can't just hand out real medical charts for people to experiment with, and even if they could, every laptop I set this project up on would probably end up configured slightly differently, which means "it works on my machine" chaos down the road.

So before touching any actual healthcare AI problem, I'm building the workspace itself first. Think of it like setting up a kitchen before you start cooking: you want the same pots, pans, and ingredients ready to go every time, no matter whose kitchen you're standing in.

## What's actually in this project

This isn't an AI model. It's two things working together:

1. **A ready-made workspace**, using something called a "dev container." Instead of writing out a long list of instructions like "install this version of Python, then this version of Java, then these ten libraries," all of that gets bundled into a container that VS Code can just open and run. Anyone (including future me, six months from now) can clone this repo, click one button, and land in an identical, fully equipped workspace. No guessing, no "wait, what version did I use again?"

2. **A source of fake patients.** There's an open source tool called Synthea that invents realistic but completely made-up patients: fake names, fake diagnoses, fake prescriptions, the whole deal. None of it is real, so there's zero privacy risk, but it's realistic enough to actually practice on. There's now a script that wires it into this environment (more on that below).

## Why bother making this its own project

Setting up a safe, repeatable environment for healthcare data work is a real pain point in the industry, not something made up to pad a portfolio. Hospitals and research teams spend a surprising amount of time just getting everyone's laptops configured the same way before any real work can even start. A clean, documented starting point like this one solves that problem on its own, before a single line of actual AI code gets written.

## What's here right now vs. what's coming

This is getting built slowly, in small pieces, instead of all at once. Here's the plan:

- [x] a dev container with Python and Java pre-installed (Java because Synthea needs it to run)
- [x] a script that downloads and runs Synthea to generate a batch of fake patients
- [ ] automated checks that stop real data or secrets from accidentally getting committed
- [ ] a walkthrough showing the whole thing working end to end

## Making fake patients

The `generate_patients.py` script is the piece that actually fills this workspace with data. You tell it how many patients you want, and it handles the rest:

- If Synthea isn't on your machine yet, it downloads it for you. It's one big file (about 200 MB), so the first run takes a bit.
- It runs Synthea, which spits out a batch of made-up people along with their whole medical history: doctor visits, diagnoses, medications, allergies, that kind of thing.
- It sorts the results into a `generated-patients/` folder. Inside, `csv/` has spreadsheet-style tables you can open in Excel or Python, and `fhir/` has the same info in FHIR, which is just the standard file format hospitals use to swap patient records with each other.

Why does this matter? Because now I've got a pile of patient records that look and feel like the real thing, and I can poke at them, break them, and build on them without ever worrying about anyone's privacy. Nobody in there actually exists.

The output folder is listed in `.gitignore` (a file that tells git which stuff to never save), so a batch of fake patients can't accidentally end up committed to the repo. Want fresh ones? Just run the script again. There's also a small test file, `test_generate_patients.py`, that checks the sorting logic works without needing Java or the big download.

## How to use this (once it's open)

1. Install the "Dev Containers" extension in VS Code.
2. Open this folder in VS Code.
3. When it asks "Reopen in Container?", say yes.
4. Wait a minute while it builds, then the workspace is ready to go.
5. To make some fake patients, open the terminal and run `python generate_patients.py --count 20` (or however many you want).

That's it for now. More coming soon.
