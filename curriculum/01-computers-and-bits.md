# Lesson 1: How Computers "Think"

No coding yet in this lesson — just the one idea everything else is built on.

## The one thing a computer actually understands

A computer is, at its core, an enormous number of tiny switches. Each switch
is either **on** or **off**. That's it. That's the entire vocabulary of a
computer: on, or off.

We give that on/off a name: a **bit** (short for "binary digit"). We usually
write it as `1` (on) or `0` (off).

## From bits to everything else

One bit alone can't say much — just on or off. But group them, and you can
represent more:

- 8 bits grouped together is called a **byte**. A byte can represent 256
  different values (2 multiplied by itself 8 times) — enough to represent
  one letter, like `A`, or a small number.
- String enough bytes together, following an agreed-upon pattern, and you
  can represent a word, a sentence, a photo, a song, or a video.

So when you see a photo on your phone, underneath it is just a very long,
very organized sequence of 1s and 0s that something knows how to turn back
into colors and shapes on your screen.

## Why this matters for coding

You will almost never write 1s and 0s yourself. But keeping this picture in
mind helps later on:

- Every program, no matter how advanced, eventually breaks down into simple
  on/off instructions a computer's processor can follow.
- A "program" is really just a **precise list of steps**, written in a way
  the computer (via layers of translation) can turn into those on/off
  signals.
- Computers are extremely fast but extremely literal — they do *exactly*
  what they're told, nothing more, nothing implied. Part of learning to
  code is learning to be that precise.

## Quick check (no pressure, just for fun)

Can you guess how many different values you could represent with 2 bits
instead of 1? (Hint: each bit can be 0 or 1, and you're combining two of
them.)

We'll pick this up in the next lesson: [What is programming?](02-what-is-programming.md)
