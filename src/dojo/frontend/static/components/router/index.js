export const initRouter = ({ onBudgetsRefresh, onBudgetsRender, onAllocationsRefresh, onAllocationsRender } = {}) => {
  const pageNodes = document.querySelectorAll(".page");
  const routeLinks = document.querySelectorAll("[data-route-link]");

  const activateRoute = (route) => {
    const normalizedRoute = route && document.querySelector(`[data-route="${route}"]`) ? route : "transactions";
    pageNodes.forEach((page) => {
      page.classList.toggle("route-page--active", page.dataset.route === normalizedRoute);
    });
    routeLinks.forEach((link) => {
      link.classList.toggle("app-header__link--active", link.dataset.routeLink === normalizedRoute);
    });
    if (normalizedRoute === "budgets" && onBudgetsRefresh) {
      onBudgetsRefresh()
        .then(() => onBudgetsRender?.())
        .catch((error) => console.error("Budgets refresh failed", error));
    }
    if (normalizedRoute === "allocations" && onAllocationsRefresh) {
      Promise.all([onBudgetsRefresh?.(), onAllocationsRefresh()])
        .then(() => {
          onBudgetsRender?.();
          onAllocationsRender?.();
        })
        .catch((error) => console.error("Allocations refresh failed", error));
    }
  };

  const handleHashChange = () => {
    const rawRoute = window.location.hash.replace("#/", "");
    activateRoute(rawRoute);
  };

  window.addEventListener("hashchange", handleHashChange);
  handleHashChange();
};
