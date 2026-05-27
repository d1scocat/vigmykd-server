# Contributing to vigmykd-api

First and foremost, thanks for taking your time to contribute! ❤️

Any type of contribution is welcome and valued. vigmykd-server has got a list of guidelines to be followed whilst contributing for the sake of easier maintenance of
the project. Take a look at the **[table of contents](#table-of-contents)** for reference. The community looks forward to your contributions 😊

Please note that the baseline for all contributions is the [Code of Conduct](./CODE_OF_CONDUCT.md).

# Table of contents

- **[How to contribute](#how-to-contribute)**
- **[How to suggest a feature](#how-to-suggest-a-feature)**
- **[How to report a bug](#how-to-report-a-bug)**
- **[Code styling](#code-styling)**
- **[Join the development team](#join-the-development-team)**

How to contribute
===
Once again, thanks for being with us! If you are here to contribute any code, extra documentation, or anything else, this paragraph is for you.

### Expectations
You should not be contributing if you have nothing to bring to the table. Here are the general guidelines:

#### What's not welcome
Contributions that...
* only focus on fixing code style;
* only optimize something;
* only add unit tests
  are **not welcome**.

In addition, contributions that largely refactor a big part of the code just for the sake of structuring are **frowned upon, but not forbidden**. However, care to document the new code structure in the commit message for it to have a chance to be accepted.

#### What's welcome
Contributions that...
* fix bugs;
* add features;
* introduce meaningful changes
  are **welcome**.

#### What should every contribution have

1) The added code must be tested.
2) The code should be reasonably optimized.

### Creating a PR
This project relies on the Git VCS for convenience. As such, you're expected to be familiar with it and how to create PRs.
### Legal notice
Developer Certificate of Origin, version 1.1
```
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.


Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```
### Commit message
A commit message must be fairly small, yet informative.
1) The first line should be the general commit idea.
2) The second line should be left empty.
3) Everything else should be wrapped to not be longer than 90 characters - if it is, put it on a new line (except for URLs).
4) If the commit message has any general links or such information (such as "References"), they should be put on the last lines.

Example of a good commit message:
```
sum: (very short summary under 50 characters)

(longer description, breaking into multiple lines whenever that
occurs to be necessary)

Reference: issue #52 (request: ...)
```

How to suggest a feature
===
Suggesting features is also contribution in a way! That said, there are some guidelines for suggesting features.
### Where to suggest features
You can suggest features in [GitHub Issues](https://github.com/d1scocat/vigmykd-server/issues).
### A good feature suggestion
What makes a good feature suggestion is the research behind it.
1) Make sure that there's no (recent) issue already open on that topic.
2) Really make sure that the feature isn't already there in some other form.

How to report a bug
===
If it's a minor bug, report it in [GitHub Issues](https://github.com/d1scocat/vigmykd-server/issues). However, if it's a major exploitable
bug or a security exploit, refrain from using issues and see the [security policy](./SECURITY.md).

Before opening an issue, please also make sure that there's no (recent) issue already open on that bug.

Code styling
===
vigmykd-api uses PEP8 with small modifications, as outlined in the [Flake8 configuration](./.flake8).

Join the development team
===
As of April 2026, the API is developed solely by me, discocat. If you're ready to dedicate time and patience to this project, [contact me](mailto:vigmykd@runderscore.com) and we'll probably figure something out!