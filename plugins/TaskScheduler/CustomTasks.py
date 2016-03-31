from NintbotForDiscord.ScheduledTask import MessageScheduledTask, RepeatingScheduledTask, ScheduledTask

__author__ = 'Riley Flynn (nint8835)'


class TaskSchedulerTask(ScheduledTask):

    def __init__(self, plugin_instance, delay = 30):
        ScheduledTask.__init__(self, delay)
        self.plugin = plugin_instance

    def construct_dict_obj(self):
        return {"type": "generic",
                "delay": self.delay}

    async def execute_task(self):
        await ScheduledTask.execute_task(self)
        self.plugin.tasks.remove(self.construct_dict_obj())


class ScheduledMessage(TaskSchedulerTask, MessageScheduledTask):

    def __init__(self, destination, message, bot_instance, plugin_instance, delay = 30):
        TaskSchedulerTask.__init__(self, plugin_instance, delay)
        MessageScheduledTask.__init__(self, destination, message, bot_instance, delay)

    def construct_dict_obj(self):
        return {"type": "message",
                "destination": self.destination.id,
                "message": self.message,
                "delay": self.delay}

    async def execute_task(self):
        await TaskSchedulerTask.execute_task(self)
        await MessageScheduledTask.execute_task(self)
