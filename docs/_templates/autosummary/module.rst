{{ fullname }}
{{ underline }}

.. contents::
    :local:

.. currentmodule:: {{fullname}}

.. automodule:: {{fullname}}

      {% if classes %}
      Classes
      =======

      .. autosummary::

	  {% for class in classes %}
	  {{ class }}
	  {% endfor %}

      {% endif %}

      {% if functions %}
      Functions
      =========

      .. autosummary::

	  {% for function in functions %}
	  {{ function }}
	  {% endfor %}

      {% endif %}

      Members
      =======






