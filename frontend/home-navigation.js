/* Home navigation enhancements — deliberately separate from simulation/API logic. */
(() => {
  const home = () => {
    step = 0;
    render();
  };
  const showHow = () => {
    home();
    requestAnimationFrame(() => {
      document.getElementById('howItWorks').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };
  document.getElementById('dashboardButton').onclick = home;
  document.getElementById('homeDashboardButton').onclick = home;
  document.getElementById('howButton').onclick = showHow;
  document.getElementById('homeHowButton').onclick = showHow;

  const about = document.querySelector('[data-info="about"]');
  const homeAbout = document.getElementById('homeAboutButton');
  const openAbout = () => {
    document.getElementById('infoKicker').textContent = 'ABOUT AASRA';
    document.getElementById('infoTitle').textContent = 'AASRA supports climate-responsive shelter design.';
    document.getElementById('infoText').textContent = 'AASRA is a guided workspace for exploring passive shelter options in demanding climates. It brings together local weather, shelter dimensions, material layers, roof and floor choices, and opening strategies so two user-defined designs can be evaluated under the same scenario. The purpose is to make thermal-comfort decisions easier to understand before detailed engineering validation.';
    document.getElementById('infoModal').hidden = false;
  };
  about.onclick = openAbout;
  homeAbout.onclick = openAbout;
})();
