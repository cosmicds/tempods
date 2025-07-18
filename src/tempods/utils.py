from datetime import datetime
# functions to aid in logging performance time
class Timer:
    """A simple timer class to measure elapsed time."""
    def __init__(self):
        self.start_time = None
        self.lap_time = None

    def start(self):
        """Start the timer."""
        self.start_time = datetime.now()
        self.lap_time = self.start_time

    def elapsed(self):
        """Return the elapsed time in seconds."""
        if self.start_time is None:
            raise RuntimeError("Timer has not been started.")
        return (datetime.now() - self.start_time).total_seconds()
    
    def reset_lap(self, msg: str = ""):
        """Set the current time as the lap time."""
        self.lap_time = datetime.now()
        if msg:
            print(f"Starting: {msg}", flush=True)
        
    def reset(self):
        """Reset the timer."""
        self.start_time = None
        self.lap_time = None
    
    def lap(self):
        """Return the time since the last lap or start."""
        if self.lap_time is None:
            raise RuntimeError("Timer has not been started.")
        elapsed = (datetime.now() - self.lap_time).total_seconds()
        self.reset_lap()
        return elapsed
def start_timer():
    """Start a timer and return it."""
    timer = Timer()
    timer.start()
    return timer
def log_time(timer: Timer, message: str):
    """Log the time taken for a specific operation."""
    elapsed_time = timer.lap()
    print(f"{message} took {elapsed_time:.2f} seconds.\n", flush=True)
    
    
    
# a decorrator to show the stack trace
# when a function is called
import traceback
def show_stack_trace(func):
    # by copilot
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        traceback.print_stack()
        return func(*args, **kwargs)
    return wrapper

# a decorator to show the stack trace
# when a function is called
def show_stack_levels(levels=None):
    # by copilot
    def decorator(func):
        def wrapper(*args, **kwargs):
            print(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
            if levels is None:
                traceback.print_stack()
            else:
                stack = traceback.format_stack()
                print("".join(stack[-levels:]))
            return func(*args, **kwargs)
        return wrapper
    return decorator