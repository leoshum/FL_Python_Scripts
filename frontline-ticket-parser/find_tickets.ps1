[CmdletBinding()]
param (
	[ValidateNotNullOrEmpty()]
	[string]
	$Repository_path = "C:\Users\mykha\source\repos\CW-0575-IEP",
	[Parameter(Mandatory)]
	[string]
	$Ticket_number
)

Set-Location $Repository_path

$git_result = git log --grep=$($Ticket_number)


if ($null -eq $git_result) {
	throw 'Tickets with specified number not founded'
}

$tickets = New-Object System.Collections.ArrayList
$start_commit_row = -1
for ($row_index = 0; $row_index -lt $git_result.Count; $row_index++) {
	if ($git_result[$row_index] -match "^commit [0-9a-f]{40}$") {
		if ($start_commit_row -eq -1) {
			$start_commit_row = $row_index
			continue
		} 
		
		$_ = $tickets.Add($git_result[$start_commit_row..($row_index - 1)])

		$start_commit_row = $row_index
	}

	if ($row_index -eq $git_result.Count - 1 -and $start_commit_row -eq 0) {
		$_ = $tickets.Add($git_result[$start_commit_row..($row_index - 1)])
	}
}

return (ConvertTo-Json $tickets -Compress)