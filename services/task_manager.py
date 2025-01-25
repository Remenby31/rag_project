import uuid
from threading import Thread
from utils.logger import logger

class TaskManager:
    def __init__(self):
        self.tasks = {}
        logger.info("TaskManager initialized")
    
    def create_task(self, task_id=None, initial_data=None):
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        self.tasks[task_id] = {
            'status': 'queued',
            'progress': 0,
            'current_file': None,
            'results': None,
            'error': None
        }
        
        if initial_data:
            self.tasks[task_id].update(initial_data)
            
        logger.info(f"Created new task with ID: {task_id}")
        return task_id
    
    def get_task_status(self, task_id):
        if task_id not in self.tasks:
            logger.warning(f"Attempted to get status for non-existent task ID: {task_id}")
            return None
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id, status_data):
        if task_id in self.tasks:
            self.tasks[task_id].update(status_data)
            logger.debug(f"Updated task {task_id} with status: {status_data}")
        else:
            logger.error(f"Attempted to update non-existent task ID: {task_id}")
    
    def run_async_task(self, task_id, target_func, *args):
        logger.info(f"Starting async task {task_id}")
        thread = Thread(target=target_func, args=(task_id, *args))
        thread.start()
        logger.debug(f"Thread started for task {task_id}")

    def get_all_tasks(self):
        return self.tasks
