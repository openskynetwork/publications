"""Regression checks for topical classification, not scientific eligibility."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from generate_publication_graphs import Entry, classify, entry_text, source_mentions, parse_as_of, display_year


class TopicClassificationTests(unittest.TestCase):
    def category(self, title):
        return classify(title)[0]

    def test_venue_and_source_names_do_not_create_topics(self):
        plain = Entry('inproceedings', 'example', {'title': 'A new study'})
        symposium = Entry('inproceedings', 'example', {'title': 'A new study', 'booktitle': 'The 14th OpenSky Symposium'})
        self.assertEqual(classify(entry_text(plain)), classify(entry_text(symposium)))
        self.assertEqual(self.category('OpenSky ADS-B'), 'Other')
        self.assertEqual(source_mentions('OpenSky ADS–B'), 'OpenSky; ADS-B')

    def test_applications_beat_methods_and_data_sources(self):
        cases = {
            'Fuel consumption prediction using deep learning and ADS-B trajectories': 'Aircraft Performance & Environmental Impact',
            'Learning Air Traffic Conflict Resolution via Adversarial Inverse Reinforcement Learning': 'Air Traffic Management',
            'Trace-Driven Evaluation of Post-Quantum Authentication for ADS-B Using OpenSky Network Data': 'Cybersecurity & Anomaly Detection',
            'Data Quality and Predictive Reliability in AI-Enabled Aviation Energy Management': 'Aircraft Performance & Environmental Impact',
            'HARP Tracker: Modular Ground Station Control for Interconnected Ballooning Missions': 'Other',
            'AI-powered disease surveillance and predictive analytics': 'Societal & Public-Service Applications',
            'Calibrating plateau detectors in ADS-B data without ground truth': 'Surveillance Infrastructure & Data Quality',
            'Generative Models for ADS-B Aircraft Trajectories': 'Trajectory Prediction & Generation',
            'Facility Coverage Gaps in Emergency Air-Medical Logistics': 'Societal & Public-Service Applications',
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(self.category(title), expected)

    def test_no_substring_or_repeated_phrase_bonus(self):
        self.assertEqual(self.category('Surface characterisation'), 'Other')
        self.assertEqual(classify('fuel burn')[1], 12)
        self.assertEqual(classify('fuel burn fuel burn')[1], 12)
        self.assertEqual(classify('aircraft noise')[1], 12)

    def test_date_label_and_month_compatibility(self):
        self.assertEqual(display_year(2026, parse_as_of('2026-10-18')), '2026\n18 Oct 2026')
        self.assertEqual(parse_as_of('2026-10').day, 1)


if __name__ == '__main__':
    unittest.main()
