import click
import json
import os
from pathlib import Path
import webbrowser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
import subprocess

load_dotenv()

llm = ChatOpenAI(model="gpt-3.5-turbo-1106")
'''
response = llm.invoke(
    [HumanMessage(content="How to setup a react native project? Can you include steps in json format with stepNumber as key, and the object containing: {summary, commandOrCode, detailedDescription}, mark any variables prefixed with $, and commands should be working")]
)
print(response.content)
'''

@click.group()
def cli():
    pass

@cli.command()
@click.option('--email', prompt=True)
@click.option('--name', prompt=True)
def setup(email, name):
    """Setup user information."""
    config = {'email': email, 'name': name}
    config_path = Path.home() / '.dincon' / 'config.json'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f)
    click.echo(f"Setup complete for {name} ({email})")

@cli.command()
def login():
    """Login and store token."""
    # Open web page for login
    webbrowser.open('https://example.com/login')
    token = click.prompt('Enter the token from the web page')
    token_path = Path.home() / '.dincon' / 'token.txt'
    with open(token_path, 'w') as f:
        f.write(token)
    click.echo("Login successful")

@cli.command()
def logout():
    """Logout and remove stored token."""
    token_path = Path.home() / '.dincon' / 'token.txt'
    if token_path.exists():
        os.remove(token_path)
        click.echo("Logged out successfully")
    else:
        click.echo("No active session found")

@cli.command()
def init():
    """Initialize a .dincon repository."""
    if Path('.dincon.json').exists():
        click.echo(".dincon.json already exists")
        return
    
    title = click.prompt("Enter project title")
    description = click.prompt("Enter project description")
    
    # TODO: Implement code analysis for existing projects
    
    data = {
        'title': title,
        'description': description
    }
    with open('.dincon.json', 'w') as f:
        json.dump(data, f, indent=2)
    click.echo("Initialized .dincon repository")

@cli.command()
@click.argument('task', nargs=-1)
def plan(task):
    """Break down a high-level task into atomic actionable tasks."""
    task_description = ' '.join(task)
    response = llm.invoke([
        HumanMessage(content=f"Break down the following task into atomic actionable steps: \"{task_description}.\""
                             f"Provide the output as a JSON object, where key is the 'stepNumber', and value has "
                             f"{'summary',  'type', 'value', } fields, where type can be oneof(code|command|description), and value should be the actual code/command/description."
                             f"I do not want a text description, only the JSON object."
                             )
    ])
    
    try:
        print(response.content)
        plan_data = json.loads(response.content)
        with open('.dincon_plan.json', 'w') as f:
            json.dump(plan_data, f, indent=2)
        click.echo("Plan created and saved to .dincon_plan.json")
        for step in plan_data:
            click.echo(f"{step['stepNumber']}. {step['summary']}")
    except json.JSONDecodeError:
        click.echo("Error: Unable to parse the plan. Please try again.")

@cli.command()
@click.option('--step', type=int, default=1, help='Step number to execute')
def execute(step):
    """Execute one actionable task and make necessary code changes."""
    if not Path('.dincon_plan.json').exists():
        click.echo("No plan found. Please run 'plan' command first.")
        return
    
    with open('.dincon_plan.json', 'r') as f:
        plan_data = json.load(f)
    
    if step < 1 or step > len(plan_data):
        click.echo(f"Invalid step number. Please choose a step between 1 and {len(plan_data)}.")
        return
    
    current_step = plan_data[step - 1]
    click.echo(f"Executing step {step}: {current_step['summary']}")
    
    response = llm.invoke([
        HumanMessage(content=f"Implement the following task: {current_step['description']}. "
                             f"Provide the necessary code changes as a series of file edits.")
    ])
    
    # TODO: Parse the AI response and apply the suggested code changes
    click.echo("AI suggestions:")
    click.echo(response.content)
    click.echo("Please review and manually apply the suggested changes.")

@cli.command()
def commit():
    """Commit the changes made during 'play' command."""
    if not Path('.git').exists():
        click.echo("This is not a Git repository. Please initialize Git first.")
        return
    
    # Stage all changes
    subprocess.run(['git', 'add', '.'])
    
    # Prompt for commit message
    commit_message = click.prompt("Enter commit message")
    
    # Commit changes
    result = subprocess.run(['git', 'commit', '-m', commit_message], capture_output=True, text=True)
    
    if result.returncode == 0:
        click.echo("Changes committed successfully.")
    else:
        click.echo(f"Error committing changes: {result.stderr}")

@cli.command()
def abort():
    """Revert code changes made during 'play' command."""
    if not Path('.git').exists():
        click.echo("This is not a Git repository. Cannot revert changes.")
        return
    
    # Check if there are uncommitted changes
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    
    if result.stdout:
        # There are uncommitted changes
        click.confirm("There are uncommitted changes. Do you want to revert them?", abort=True)
        subprocess.run(['git', 'reset', '--hard'])
        click.echo("Changes reverted successfully.")
    else:
        click.echo("No changes to revert.")

# TODO: Implement plan, play, commit, and abort commands

if __name__ == '__main__':
    cli()