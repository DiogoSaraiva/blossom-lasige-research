# LASIGE - Summer of Research

This repo contains my research work regarding the **LASIGE Summer of Research 2025**, based on the **Blossom** platform.

It uses **PyCharm**, **Python 3.12**, and is deployed with **Docker**.


##   Project Structure

```
blossom-lasige-research/
├── Dockerfile
├── .gitignore
├── .gitmodules
└── open_hmi/
    ├── blossom_public/
    ├── Hardware/
    ├── OpenSense Workspace/
    ├── Robot Server Codebase/
    ├── Skin/
    ├── .gitmodules
    └── README.md

```

## First Steps – Configure Development Environment

If you are a student, you may apply for a free JetBrains Student Pack.  
Just go to [their page](https://www.jetbrains.com/academy/student-pack/) and redeem it.

Install **WSL 2.0 Ubuntu** (tested on Ubuntu 24.04) and, if you haven’t done so already, [configure your SSH keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh).

Then, with PyCharm already installed and running, click on **"Clone Repository"**, enter:
```
https://github.com/DiogoSaraiva/blossom-lasige-research.git
```

----------

## SSH Authentication

In order to push, you need to use SSH authentication.  
To change from HTTPS to SSH, run the following:

```bash
cd blossom-lasige-research
git remote set-url origin git@github.com:DiogoSaraiva/blossom-lasige-research.git

cd open_hmi
git remote set-url origin git@github.com:DiogoSaraiva/OpenHMI.git

cd blossom_public
git remote set-url origin git@github.com:DiogoSaraiva/blossom-public.git
```
##  License

This project inherits the license from the original project [blossom-public](https://github.com/hrc2/blossom-public). 
Additional work here present may follow additional license.
