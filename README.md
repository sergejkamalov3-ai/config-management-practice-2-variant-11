# Этап 4. Порядок загрузки зависимостей

`sh run.sh examples/test.yaml` выводит D → B → C → A. `examples/cycle.yaml` показывает цикл X → Y → Z → X.

### Результаты проверки Apache Maven 3.9.15

| Корень | Этап 4, порядок подготовки | Maven, завершение загрузки JAR при пустом кэше |
|---|---|---|
| junit 4.13.2 | hamcrest-core → junit | junit → hamcrest-core |
| hamcrest-library 1.3 | hamcrest-core → hamcrest-library | hamcrest-library → hamcrest-core |
| hamcrest-core 1.3 | hamcrest-core | hamcrest-core |

Во всех трёх случаях совпали узлы и рёбра графа программы и поддерева Maven.
Этап 4 выдаёт допустимую последовательность использования пакетов с учётом их зависимостей.
Физическое скачивание файлов допускает другую последовательность. Значения в таблице относятся к указанному запуску.

[Журнал проверки и архив maven-comparison с PNG, Mermaid и деревьями Maven](https://github.com/sergejkamalov3-ai/config-management-practice-2-variant-11/actions/runs/44735893653).
