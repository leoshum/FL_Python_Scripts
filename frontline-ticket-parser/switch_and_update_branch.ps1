[CmdletBinding()]
param (
	[ValidateNotNullOrEmpty()]
	[string]
	$Repository_path = "C:\Users\mykha\source\repos\CW-0575-IEP",
	[ValidateNotNullOrEmpty()]
	[string]
	$Branch_name = "main",
	[ValidateNotNullOrEmpty()]
	[string]
	$Key_Path = "~/.ssh/a2c"
)

Set-Location $Repository_path/

git config core.sshCommand "ssh -i $Key_Path"

$branchExistsLocally = git branch --list $Branch_name

if ($branchExistsLocally) {
    # If the 'main' branch exists locally, switch to it
    git checkout $Branch_name
} else {
    # If the 'main' branch doesn't exist locally, checkout from the remote repository
    git checkout --track origin/$($Branch_name)
}

git pull