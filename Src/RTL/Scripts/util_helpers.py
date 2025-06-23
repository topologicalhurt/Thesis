import subprocess as sp


def get_git_author() -> tuple[str, str] | None:
    """# Summary

    Get the current user's git credentials via shell

    ## Returns:
        tuple[str, str] | None: the tuple of (author_name, author_email) if the credentials could be found,
        None otherwise
    """
    try:
        name_args = ['git', 'config', '--get', 'user.name']
        author = sp.run(name_args, capture_output=True, text=True, check=True)
        author = author.stdout.strip()

        email_args = ['git', 'config', '--get', 'user.email']
        author_email = sp.run(email_args, capture_output=True, text=True, check=True)
        author_email = author_email.stdout.strip()
    except (sp.CalledProcessError, FileNotFoundError) as e:
        print(f'Error retrieving git config: {e}')
        return None
    return author, author_email
