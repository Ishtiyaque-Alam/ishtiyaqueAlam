import time
import sys
import typer

def type_text(text: str, delay: float = 0.005):
    """
    Simulates a typing animation by printing text character by character.

    Args:
        text (str): The string to display.
        delay (float): The delay in seconds between each character.
    """
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    # Print a newline at the end to ensure the next prompt starts on a new line
    print()

def main():
    """
    A simple CLI application that uses a typing animation for its output.
    """
    typer.echo("Starting the CLI program...")
    typer.echo("--------------------------")

    welcome_message = "Hello! Welcome to the Typer Animation Demo. I will now generate a response with a typing animation."
    
    # Call the function to display the text with a typing effect
    type_text(welcome_message)

    response_text = "This is a longer response from the 'model'. You can see how the text appears slowly, as if it's being typed out in real time. This technique is often used to make CLI applications more engaging and conversational. You can adjust the speed by changing the 'delay' argument."

    # Use the typing animation for the "model's" response
    type_text(response_text)

    typer.echo("--------------------------")
    typer.echo("The program has finished.")

if __name__ == "__main__":
    typer.run(main)