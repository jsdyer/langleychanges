import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refresh import reconcile,parse_city,safe_url

class SourceTests(unittest.TestCase):
    def record(self,status='ACTIVE'):return dict(id='one',title='Test',status=status,description='Homes',application='DP1',community='Willoughby',date='2020-01-01',documents=[],milestones=[])
    def test_baseline_change_disappearance_and_reappearance(self):
        a=reconcile([self.record()],{},'2026-01-01');self.assertTrue(a[0]['baseline']);self.assertEqual(a[0]['history'],[])
        b=reconcile([self.record('COMPLETE')],{'records':a},'2026-02-01');self.assertEqual(b[0]['history'][0]['changes']['status']['before'],'ACTIVE');self.assertEqual(b[0]['first_seen'],'2026-01-01')
        c=reconcile([],{'records':b},'2026-03-01');self.assertEqual(c[0]['missing_since'],'2026-03-01');self.assertEqual(c[0]['status'],'COMPLETE')
        d=reconcile([self.record('COMPLETE')],{'records':c},'2026-04-01');self.assertEqual(d[0]['missing_since'],'');self.assertEqual(d[0]['history'][-1]['changes']['listed'],{'before':False,'after':True})
    def test_new_after_baseline_and_no_false_repeat_changes(self):
        a=reconcile([self.record()],{},'2026-01-01');b=reconcile([self.record()],{'records':a},'2026-01-02');self.assertEqual(b[0]['history'],[])
        r=self.record();r['id']='two';c=reconcile([self.record(),r],{'records':b},'2026-01-03');self.assertFalse(c[1]['baseline'])
    def test_city_parser_excludes_contact_details_and_keeps_document_links(self):
        html=''.join(f'<button class="accordion__trigger" id="b{i}" aria-controls="a{i}">Example {i}</button><div id="a{i}"><p>Current status: Review</p><p><strong>Description:</strong> New homes<br><strong>Application type:</strong> Permit<br><strong>Applicant contact:</strong> Private name 555</p><p>Application progress:</p><ul><li>Application submitted: March 6, 2026</li></ul><a href="/plans.pdf">Plans</a></div>' for i in range(10))
        rows=parse_city(html);self.assertEqual(len(rows),10);self.assertEqual(rows[0]['date'],'2026-03-06');self.assertEqual(rows[0]['documents'][0]['url'],'https://www.langleycity.ca/plans.pdf');self.assertNotIn('Private name',str(rows));self.assertEqual(rows[0]['description'],'New homes');self.assertEqual(rows[0]['application'],'Permit')
        with self.assertRaises(ValueError):parse_city(html.replace('Current status:','Changed schema:'))
    def test_untrusted_links_and_empty_links(self):
        self.assertEqual(safe_url('javascript:alert(1)'),'');self.assertEqual(safe_url(''),'')
