# the ratings installed before 20.0.1.1.0 keep their data (noupdate): place them on the 9-box grid
LEVELS = {
    'rating_needs_improvement': 'low',
    'rating_meets': 'medium',
    'rating_exceeds': 'high',
    'rating_outstanding': 'high',
}


def migrate(cr, version):
    for name, level in LEVELS.items():
        cr.execute("""
            UPDATE hr_appraisal_rating rating
               SET performance_level = %s
              FROM ir_model_data data
             WHERE data.module = 'om_hr_appraisal' AND data.name = %s
               AND data.model = 'hr.appraisal.rating' AND data.res_id = rating.id
        """, (level, name))
    # the appraisals hold the level of their rating
    cr.execute("""
        UPDATE hr_appraisal appraisal
           SET performance_level = rating.performance_level
          FROM hr_appraisal_rating rating
         WHERE appraisal.rating_id = rating.id
           AND appraisal.performance_level IS DISTINCT FROM rating.performance_level
    """)
