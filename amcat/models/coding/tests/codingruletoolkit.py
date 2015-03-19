###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################
import json
from amcat.models import CodingRule, CodingSchemaField, Code
from amcat.models.coding.codingruletoolkit import schemarules_valid, parse, to_json, EQUALS, \
    clean_tree, NOT, OR
from amcat.models.coding.codingschema import ValidationError

from amcat.tools import amcattest


class TestCodingRuleToolkit(amcattest.AmCATTestCase):
    def condition(self, s, c):
        return CodingRule(codingschema=s, condition=c)

    def test_schemafield_valid(self):
        schema_with_fields = amcattest.create_test_schema_with_fields()
        schema = schema_with_fields[0]

        self.assertTrue(schemarules_valid(schema))
        self.condition(schema, "()").save()
        self.assertTrue(schemarules_valid(schema))
        self.condition(schema, "(3==2)").save()
        self.assertFalse(schemarules_valid(schema))

        CodingRule.objects.all().delete()

        # Test multiple (correct) rules
        self.condition(schema, "()").save()
        self.condition(schema, "()").save()
        self.condition(schema, "()").save()
        self.assertTrue(schemarules_valid(schema))
        self.condition(schema, "(3==2)").save()
        self.assertFalse(schemarules_valid(schema))


    def test_to_json(self):
        import functools

        o1, o2 = amcattest.create_test_code(), amcattest.create_test_code()
        schema_with_fields = amcattest.create_test_schema_with_fields()
        code_field = schema_with_fields[4]
        c = functools.partial(self.condition, schema_with_fields[0])

        tree = to_json(parse(c("{}=={}".format(code_field.id, o1.id))))
        self.assertEquals(json.loads(tree), {"type": EQUALS, "values": [
            {"type": "codingschemafield", "id": code_field.id},
            {"type": "code", "id": o1.id}
        ]})

        tree = parse(c("{}=={}".format(code_field.id, o1.id)))
        self.assertEquals(json.dumps(to_json(tree, serialise=False)), to_json(tree))


    def test_clean_tree(self):
        import functools

        o1, o2 = amcattest.create_test_code(), amcattest.create_test_code()
        codebook, codebook_codes = amcattest.create_test_codebook_with_codes()
        schema_with_fields = amcattest.create_test_schema_with_fields(codebook=codebook)

        schema = schema_with_fields[0]
        code_field = schema_with_fields[4]

        c = functools.partial(self.condition, schema)

        tree = parse(c("{code_field.id}=={o1.id}".format(**locals())))
        self.assertRaises(ValidationError, clean_tree, schema, tree)
        tree = parse(c("{code_field.id}=={code.id}".format(code_field=code_field, code=codebook.codes[0])))
        self.assertEquals(clean_tree(schema, tree), None)
        self.assertRaises(ValidationError, clean_tree, amcattest.create_test_schema_with_fields()[0], tree)

    def test_parse(self):
        import functools

        o1, o2 = amcattest.create_test_code(), amcattest.create_test_code()
        schema_with_fields = amcattest.create_test_schema_with_fields()

        schema = schema_with_fields[0]
        codebook = schema_with_fields[1]

        text_field = schema_with_fields[2]
        number_field = schema_with_fields[3]
        code_field = schema_with_fields[4]

        c = functools.partial(self.condition, schema)

        # Empty conditions should return None
        self.assertEquals(parse(c("")), None)
        self.assertEquals(parse(c("()")), None)

        # Recursion should be checked for
        cr = CodingRule.objects.create(codingschema=schema, label="foo", condition="()")
        cr.condition = str(cr.id)
        self.assertRaises(SyntaxError, parse, cr)

        # Nonexisting fields should raise an error
        cr.condition = "0==2"
        self.assertRaises(CodingSchemaField.DoesNotExist, parse, cr)
        cr.condition = "{}==0".format(code_field.id)
        self.assertRaises(Code.DoesNotExist, parse, cr)
        cr.condition = "0"
        self.assertRaises(CodingRule.DoesNotExist, parse, cr)
        cr.condition = "{}=={}".format(code_field.id, o1.id)
        self.assertTrue(parse(cr) is not None)

        # Wrong inputs for fields should raise an error
        for inp in ("'a'", "0.2", "u'a'"):
            cr.condition = "{}=={}".format(number_field.id, inp)
            self.assertRaises(SyntaxError, parse, cr)

        for inp in ("'a'", "0.2", "u'a'", repr(str(o1.id))):
            cr.condition = "{}=={}".format(code_field.id, inp)
            self.assertRaises(SyntaxError, parse, cr)

        for inp in ("'a'", "0.2", "2"):
            cr.condition = "{}=={}".format(text_field.id, inp)
            self.assertRaises(SyntaxError, parse, cr)

        # "Good" inputs shoudl not yield an error
        for field, inp in ((number_field, 1), (text_field, "u'a'"), (code_field, o1.id)):
            cr.condition = "{}=={}".format(field.id, inp)
            self.assertTrue(parse(cr) is not None)

        # Should accept Python-syntax (comments, etc)
        cr.condition = """{}==(
        # This should be a comment)
        {})""".format(text_field.id, "u'a'")
        self.assertTrue(parse(cr) is not None)

        ## Testing output
        tree = parse(c("not {}".format(cr.id)))
        self.assertEquals(tree["type"], NOT)
        self.assertTrue(not isinstance(tree["value"], CodingRule))

        tree = parse(c("{}=={}".format(text_field.id, "u'a'")))
        self.assertEquals(tree, {"type": EQUALS, "values": (text_field, u'a')})

        cr.save()
        tree = parse(c("{cr.id} or {cr.id}".format(cr=cr)))
        self.assertEquals(tree, {"type": OR, "values": (parse(cr), parse(cr))})

        # Should accept greater than / greater or equal to / ...
        parse(c("{number_field.id} > 5".format(**locals())))
        parse(c("{number_field.id} < 5".format(**locals())))
        parse(c("{number_field.id} >= 5".format(**locals())))
        parse(c("{number_field.id} <= 5".format(**locals())))

        # ..but not if schemafieldtype is text or code
        self.assertRaises(SyntaxError, parse, c("{text_field.id} > 5".format(**locals())))
        self.assertRaises(SyntaxError, parse, c("{code_field.id} > 5".format(**locals())))

