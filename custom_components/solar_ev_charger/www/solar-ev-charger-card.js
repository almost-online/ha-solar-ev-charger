class SolarEVChargerCard extends HTMLElement {
  set hass(hass) {
    if (!this.content) {
      this.innerHTML = `
        <ha-card header="Solar EV Charger Flow">
          <div class="card-content">
            <style>
              .flow-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 20px;
                padding: 10px;
              }
              .row {
                display: flex;
                justify-content: space-around;
                width: 100%;
                align-items: center;
              }
              .node {
                display: flex;
                flex-direction: column;
                align-items: center;
                width: 80px;
              }
              .icon-circle {
                width: 50px;
                height: 50px;
                border-radius: 50%;
                border: 2px solid var(--primary-color);
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 5px;
                position: relative;
              }
              .value {
                font-size: 0.9em;
                font-weight: bold;
              }
              .label {
                font-size: 0.8em;
                opacity: 0.7;
              }
              .connection {
                flex-grow: 1;
                height: 2px;
                background: var(--divider-color);
                position: relative;
              }
              .arrow {
                position: absolute;
                top: -4px;
                width: 10px;
                height: 10px;
                border-top: 2px solid var(--divider-color);
                border-right: 2px solid var(--divider-color);
                transform: rotate(45deg);
              }
              .arrow.right { right: 0; }
              .arrow.left { left: 0; transform: rotate(225deg); }
              .vertical-connection {
                width: 2px;
                height: 20px;
                background: var(--divider-color);
                position: relative;
              }
            </style>
            <div class="flow-container" id="container">
            </div>
          </div>
        </ha-card>
      `;
      this.content = this.querySelector("#container");
    }

    const config = this._config;
    const entityId = config.entity;
    const state = hass.states[entityId];

    if (!state) {
      this.content.innerHTML = "Entity not found";
      return;
    }

    const data = state.attributes;
    const solar = Math.round(data.solar || 0);
    const grid = Math.round(data.grid || 0);
    const consumption = Math.round(data.consumption || 0);
    const battery = Math.round(data.battery_power || 0);
    const ev = Math.round(data.ev_power || 0);
    const soc = Math.round(data.battery_soc || 0);

    this.content.innerHTML = `
      <div class="row">
        <div class="node">
          <div class="icon-circle"><ha-icon icon="mdi:solar-panel-large"></ha-icon></div>
          <div class="value">${solar}W</div>
          <div class="label">Solar</div>
        </div>
        <div class="connection"><div class="arrow right"></div></div>
        <div class="node">
          <div class="icon-circle"><ha-icon icon="mdi:home"></ha-icon></div>
          <div class="value">${consumption}W</div>
          <div class="label">Home</div>
        </div>
        <div class="connection"><div class="arrow ${grid >= 0 ? 'left' : 'right'}"></div></div>
        <div class="node">
          <div class="icon-circle"><ha-icon icon="mdi:transmission-tower"></ha-icon></div>
          <div class="value">${Math.abs(grid)}W</div>
          <div class="label">${grid >= 0 ? 'Export' : 'Import'}</div>
        </div>
      </div>
      <div class="row" style="justify-content: center; gap: 40px; margin-top: 10px;">
        <div class="node">
           <div class="vertical-connection"></div>
           <div class="icon-circle">
             <ha-icon icon="mdi:battery"></ha-icon>
           </div>
           <div class="value">${soc}%</div>
           <div class="value">${Math.abs(battery)}W</div>
           <div class="label">${battery <= 0 ? 'Charging' : 'Discharging'}</div>
        </div>
        <div class="node">
           <div class="vertical-connection"></div>
           <div class="icon-circle">
             <ha-icon icon="mdi:ev-station"></ha-icon>
           </div>
           <div class="value">${ev}W</div>
           <div class="label">EV</div>
        </div>
      </div>
    `;
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("You need to define an entity");
    }
    this._config = config;
  }

  getCardSize() {
    return 3;
  }
}

customElements.define("solar-ev-charger-card", SolarEVChargerCard);
