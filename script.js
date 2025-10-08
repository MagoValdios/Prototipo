const navButtons = document.querySelectorAll('.nav-btn');
const panels = document.querySelectorAll('.panel');

navButtons.forEach((btn) => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.target;

    navButtons.forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');

    panels.forEach((panel) => {
      panel.classList.toggle('visible', panel.id === target);
    });
  });
});

const starGroups = document.querySelectorAll('.stars');

starGroups.forEach((group) => {
  const buttons = Array.from(group.querySelectorAll('button'));
  buttons.forEach((button, index) => {
    button.addEventListener('click', () => {
      buttons.forEach((b, idx) => {
        b.classList.toggle('active', idx <= index);
      });
    });
  });
});
