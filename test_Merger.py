from unittest import TestCase
import annotationMerger
import pandas as ps


class TestFilter(TestCase):

    def test_GivenChrPosKeyWithoutMatchingKeys_WhenChrPosKeyIsused_Then_ReturnChrPosKey(self):

        chromo = '1'
        seq_start = '10000'
        refAllele = 'A'
        altAllele = 'T'

        expectedChrPosKey = "{0}:{1}".format(chromo,seq_start)

        rowDic = {'chromosome': chromo, 'seq_start_position' : seq_start, 'ref_allele' : refAllele, 'alt_allele' : altAllele }
        row = ps.Series(rowDic)

        actualChrPos = annotationMerger.formatChrPosKey(row)

        self.assertEqual(expectedChrPosKey,actualChrPos)

    def test_GivenChrPosKeyWithInsertionWithMatchingFirstNucleotides_WhenChrPosKeyIsused_Then_ReturnShiftedAndHyphonatedResult(self):
        chromo = '1'
        seq_start = '10000'
        seq_shift = '10001'
        refAllele = 'A'
        altAllele = 'ATT'

        expectedChrPosKey = "{0}:{1}-{2}".format(chromo, seq_start,seq_shift)

        rowDic = {'chromosome': chromo, 'seq_start_position': seq_start, 'ref_allele': refAllele,
                  'alt_allele': altAllele}
        row = ps.Series(rowDic)

        actualChrPos = annotationMerger.formatChrPosKey(row)

        self.assertEqual(expectedChrPosKey, actualChrPos)

    def test_GivenTwoMatchingColumns_WhenRowBuilderIsCalled_Then_ReturnCorrectlyBuiltRow(self):

        # Given
        data = ["4_1804915_A/G", "4:1804915", "G", "ENSG00000068078", "ENST00000260795", "Transcript",
                "3_prime_UTR_variant", \
                "1509", "-", "-", "-", "-", "rs1466726466", \
                "IMPACT=MODIFIER;STRAND=1;VARIANT_CLASS=SNV;SYMBOL=FGFR3;SYMBOL_SOURCE=HGNC;HGNC_ID=HGNC "]

        data1 = ["4_1804915_A/G", "4:1804915", "G", "2261", "NR_148971.1", "Transcript",
                 "3_prime_UTR_variant", \
                 "1509", "-", "-", "-", "-", "rs1466726466", \
                 "IMPACT=MODIFIER;STRAND=1;BIOTYPE=lncRNA;VARIANT_CLASS=SNV;SYMBOL=FGFR3;SYMBOL_SOURCE=HGNC;HGNC_ID=HGNC "]
        colNames = ["#Uploaded_variation", "Location", "Allele", "Gene", "Feature", "Feature_type", "Consequence",
                    "cDNA_position", "CDS_position", "Protein_position", "Amino_acids", "Codons",
                    "Existing_variation",
                    "Extra"]
        tsvInputRow =  {'alt_allele': '-', 'read_depth': '11572', 'ensembl_gene_id': '', 'rs_id_Variant': '', 'Platform': 'Targeted NGS', 'ucsc_gene_id': '',
                          'ref_allele': 'T', 'chromosome': '19', 'ncbi_gene_id': '9817', 'nucleotide_change': '1225delA', 'hgnc_symbol': 'KEAP1', 'consequence': 'stop gain', 'Allele_frequency': '96,47', 'Passage': '27', 'amino_acid_change': 'M409X', 'Model_ID': 'LCF16',
                        'datasource': 'CURIE-LC', 'ensembl_transcript_id': '', 'Sample_ID': 'LCF16p27:26/08/2016', 'seq_start_position': '10491677', 'genome_assembly': 'GRCh38', 'sample_origin': 'xenograft'}

        expectedBuiltRow = ['LCF16', 'LCF16p27:26/08/2016', 'xenograft', None, '27', u'KEAP1', u'protein_coding', u'1225del', u'deletion',
         'Atg/tg', 'M409X', 'frameshift_variant', '', '11572', '96,47', '19', '10491677', 'T', '-', '', '9817',
         'NM_203500.2', None, None, '-', 'GRCh38', 'Targeted NGS']

        EMBLdf = ps.DataFrame([data], columns=colNames)
        NCBIdf = ps.DataFrame([data1], columns=colNames)
        inputRows = ps.concat([EMBLdf, NCBIdf])

        # When
        actualRows = annotationMerger.buildFinalTemplate(inputRows, tsvInputRow)

        # Then
        Row1EqualsRow0inActual = actualRows.equals(expectedRows)

        self.assertTrue(Row1EqualsRow0inActual)

