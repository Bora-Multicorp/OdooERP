{
    'name': 'Case Sensitive Widget',
    'summary': 'Provide 3 widget. '
               'Upper Case, Lower Case and Proper Case. ',
    'description': """
        This Widget will make string become to UPPERCASE, lowercase or ProperCase.
    """,
    'author': "Sonny Huynh",
    'category': 'Extra Tools',
    'version': '18.0.0.1',
    'depends': ["base"],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'case_sensitive_widget/static/src/input_field/upper_case_char_field.xml',
            'case_sensitive_widget/static/src/input_field/upper_case_char_field.js',

            'case_sensitive_widget/static/src/input_field/proper_case_char_field.xml',
            'case_sensitive_widget/static/src/input_field/proper_case_char_field.js',

            'case_sensitive_widget/static/src/input_field/lower_case_char_field.xml',
            'case_sensitive_widget/static/src/input_field/lower_case_char_field.js',
        ],
    },

    'support': 'huynh.giang.son.gs@gmail.com',
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
}