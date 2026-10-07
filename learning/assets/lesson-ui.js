/* Exact short answers only. Reasoning and course progress are reviewed in chat. */
(() => {
  'use strict';
  const normalize = value => value.trim().toLocaleLowerCase('ru').replace(/\s+/g, ' ');
  const exercises = Array.from(document.querySelectorAll('[data-exercise]'));
  const states = exercises.map(form => ({ form, attempts: 0, hinted: false, result: 'не проверено' }));
  const summary = document.querySelector('[data-summary]');
  function updateSummary() {
    if (!summary) return;
    summary.value = [document.title, 'Самоотчёт тренажёра за текущую загрузку страницы; не зачёт практики.',
      ...states.map(({ form, attempts, hinted, result }, i) =>
        `${i + 1}. ${form.dataset.title}: ${result}; попыток: ${attempts}; подсказка: ${hinted ? 'да' : 'нет'}.`),
      'Моё объяснение причины: '].join('\n');
  }
  for (const state of states) {
    const { form } = state;
    const input = form.querySelector('[data-answer]');
    const feedback = form.querySelector('[data-feedback]');
    const hint = form.querySelector('[data-hint]');
    const hintButton = form.querySelector('[data-show-hint]');
    const answers = (form.dataset.answers || '').split('|').map(normalize).filter(Boolean);
    if (!input || !feedback || !hint || !hintButton || !answers.length) continue;
    const say = (message, kind) => {
      feedback.textContent = message;
      feedback.dataset.kind = kind;
    };
    form.querySelectorAll('button').forEach(button => { button.disabled = false; });
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (!normalize(input.value)) {
        say('Введите ответ. Пустое поле не считается попыткой.', 'empty');
        input.focus();
        return;
      }
      state.attempts += 1;
      const correct = answers.includes(normalize(input.value));
      state.result = correct ? 'верный короткий ответ' : 'ошибка';
      if (correct) {
        say(`Верно ${state.hinted ? 'с подсказкой тренажёра' : 'без подсказки тренажёра'}. Попыток: ${state.attempts}. Объясните причину в чате: совпадение ответа ещё не доказывает понимание.`, 'correct');
      } else {
        say(`Пока неверно. Попытка ${state.attempts}. Проверьте условие и попробуйте снова; при необходимости откройте подсказку.`, 'incorrect');
      }
      updateSummary();
    });
    hintButton.addEventListener('click', () => {
      state.hinted = true;
      hint.hidden = false;
      hintButton.setAttribute('aria-expanded', 'true');
      say('Подсказка открыта. Она будет отмечена в отчёте после очистки ответа и следующих попыток.', 'hint');
      updateSummary();
    });
    form.addEventListener('reset', () => {
      say('Поле очищено. История попыток и подсказок сохранена.', 'reset');
      input.focus();
    });
  }
  updateSummary();
  const staticHelp = document.querySelector('[data-static-help]');
  if (staticHelp) staticHelp.hidden = true;
})();
