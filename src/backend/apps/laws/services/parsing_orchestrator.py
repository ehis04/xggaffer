from apps.referee.Laws.models import LawEdition, Law, LawClause, LawChange, ParsingJob
from apps.laws.utils.pdf_processor import PDFProcessor
from apps.laws.services.llm_parser import LawsLLMParser
from django.utils import timezone
from django.db import transaction

class ParsingOrchestrator:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.llm_parser = LawsLLMParser()
    
    def parse_edition(self, edition_id: int, use_vision: bool = True):
        edition = LawEdition.objects.get(id=edition_id)
        
        job = ParsingJob.objects.create(
            edition=edition,
            status='processing',
            started_at=timezone.now()
        )
        
        try:
            pdf_path = edition.pdf_file.path
            
            law_sections = self.pdf_processor.split_pdf_by_law(pdf_path)
            
            parsed_laws = []
            
            for law_number, start_page, end_page in law_sections:
                print(f"Processing Law {law_number} (pages {start_page}-{end_page})")
                
                if use_vision:
                    all_images = self.pdf_processor.pdf_to_images(pdf_path)
                    law_images = all_images[start_page:end_page + 1]
                    
                    parsed_law = self.llm_parser.parse_law_from_images(law_images, law_number)
                else:
                    pass
                
                parsed_laws.append(parsed_law)
            
            job.parsed_data = {'laws': parsed_laws}
            job.status = 'review'
            job.save()
            
            return job
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            raise
    
    @transaction.atomic
    def approve_and_save(self, job_id: int):
        job = ParsingJob.objects.get(id=job_id)
        
        if job.status != 'review':
            raise ValueError("Job must be in review status")
        
        edition = job.edition
        parsed_data = job.parsed_data
        
        Law.objects.filter(edition=edition).delete()
        
        for law_data in parsed_data['laws']:
            law = Law.objects.create(
                edition=edition,
                number=law_data['law_number'],
                title=law_data['title'],
                full_content=law_data
            )

            for clause_data in law_data.get('clauses', []):
                LawClause.objects.create(
                    law=law,
                    clause_id=clause_data['clause_id'],
                    heading=clause_data.get('heading', ''),
                    content=clause_data['content'],
                    examples=clause_data.get('examples', []),
                    notes=clause_data.get('notes', []),
                    order=clause_data.get('order', 0)
                )
        
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.save()
        
        return job
    
    def detect_changes(self, old_edition_id: int, new_edition_id: int):
        old_edition = LawEdition.objects.get(id=old_edition_id)
        new_edition = LawEdition.objects.get(id=new_edition_id)
        
        old_laws = {law.number: law for law in old_edition.laws.all()}
        new_laws = {law.number: law for law in new_edition.laws.all()}
        
        all_changes = []
        
        for law_num in new_laws.keys():
            if law_num in old_laws:
                changes = self.llm_parser.compare_editions(
                    old_laws[law_num].full_content,
                    new_laws[law_num].full_content
                )

                for change in changes:
                    LawChange.objects.create(
                        edition=new_edition,
                        law_number=law_num,
                        clause_id=change.get('clause_id', ''),
                        change_type=change['change_type'],
                        description=change['description'],
                        old_content=change.get('old_content', ''),
                        new_content=change.get('new_content', '')
                    )
                
                all_changes.extend(changes)
        
        return all_changes