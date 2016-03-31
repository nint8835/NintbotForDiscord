import time

__author__ = 'Riley Flynn (nint8835)'


class ScheduledTask:

    def __init__(self, delay = 30):
        self.created = time.time()
        self.delay = delay

    def check_task(self):
        return time.time() - self.created >= self.delay

    async def execute_task(self):
        pass


class RepeatingScheduledTask(ScheduledTask):

    def __init__(self, scheduler, delay=30):
        ScheduledTask.__init__(self, delay)
        self.scheduler = scheduler

    async def execute_task(self):
        self.created = time.time()
        self.scheduler.add_task(self)


class RepeatingScheduledTaskWrapper(RepeatingScheduledTask):

    def __init__(self, task, scheduler):
        RepeatingScheduledTask.__init__(self, scheduler, task.delay)
        self.task = task
        self.scheduler = scheduler

    def check_task(self):
        return self.task.check_task()

    async def execute_task(self):
        await RepeatingScheduledTask.execute_task(self)
        await self.task.execute_task()


class MessageScheduledTask(ScheduledTask):

    def __init__(self, destination, message, bot_instance, delay=30):
        ScheduledTask.__init__(self, delay)
        self.destination = destination
        self.message = message
        self.bot = bot_instance

    async def execute_task(self):
        await self.bot.send_message(self.destination, self.message)


class RepeatingMessageScheduledTask(RepeatingScheduledTask, MessageScheduledTask):

    def __init__(self, destination, message, bot_instance, scheduler, delay=30):
        RepeatingScheduledTask.__init__(self, scheduler, delay)
        MessageScheduledTask.__init__(self, destination, message, bot_instance, delay)

    async def execute_task(self):
        await RepeatingMessageScheduledTask.execute_task(self)
        await MessageScheduledTask.execute_task(self)
