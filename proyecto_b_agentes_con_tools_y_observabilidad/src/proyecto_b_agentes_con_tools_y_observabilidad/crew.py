from dotenv import load_dotenv

_ = load_dotenv()

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, FileWriterTool

#================================ LANGFUSE ===============================
# Lee LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY y LANGFUSE_BASE_URL del .env
from langfuse import get_client
from openinference.instrumentation.crewai import CrewAIInstrumentor
from openinference.instrumentation.litellm import LiteLLMInstrumentor

langfuse = get_client()

# CrewAI -> spans de Crew, Agente, Tarea y Tool (latencia de cada uno)
CrewAIInstrumentor().instrument(skip_dep_check=True)
# LiteLLM -> generaciones con modelo y tokens (Langfuse calcula el costo)
LiteLLMInstrumentor().instrument()

serper = SerperDevTool() #TAVILY
scraper = ScrapeWebsiteTool() #APIfy
file_writer = FileWriterTool() #Crear Archivos

@CrewBase
class CrearPublicacionBlogConHerramientas():
	"""Equipo CrearPublicacionBlogConHerramientas"""

	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'

	@agent
	def investigador_de_contenido(self) -> Agent:
		return Agent(
			config=self.agents_config['investigador_de_contenido'],
			tools=[serper],
			verbose=True
		)

	@agent
	def planificador_de_contenido(self) -> Agent:
		return Agent(
			config=self.agents_config['planificador_de_contenido'],
			tools=[scraper],
			verbose=True
		)

	@agent
	def escritor_del_blog(self) -> Agent:
		return Agent(
			config=self.agents_config['escritor_del_blog'],
			verbose=True
		)

	@agent
	def revisor_de_contenido(self) -> Agent:
		return Agent(
			config=self.agents_config['revisor_de_contenido'],
			verbose=True
		)

	#================================= TAREAS ================================
	@task
	def investiga_contenido(self) -> Task:
		return Task(
			config=self.tasks_config['investiga_contenido'],
		)

	@task
	def planifica_contenido(self) -> Task:
		return Task(
			config=self.tasks_config['planifica_contenido'],
		)

	@task
	def escribe_post_blog(self) -> Task:
		return Task(
			config=self.tasks_config['escribe_post_blog'],
		)

	@task
	def revisa_contenido(self) -> Task:
		return Task(
			config=self.tasks_config['revisa_contenido'],
		)

	@task
	def guarda_contenido(self) -> Task:
		return Task(
			config=self.tasks_config['guarda_contenido'],
			tools=[file_writer]
		)
	
	@crew
	def equipo(self) -> Crew:
		"""Crea el equipo CrearPublicacionBlogConHerramientas"""

		return Crew(
			agents=self.agents,  # Creado automáticamente por el decorador @agent
			tasks=self.tasks,    # Creado automáticamente por el decorador @task
			process=Process.sequential,
			verbose=True,
		)
