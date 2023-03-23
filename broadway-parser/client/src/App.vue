<template>
  <div id="app">
    <img alt="Vue logo" src="./assets/logo.png">

    <div class="table-wrapper">
      <p>https://www.telecharge.com/ticketsearchresults.aspx?ProductId={{productId}}</p>
      <div class="table-header">
        <b-pagination v-model="currentPage" :total-rows="items.length" :per-page="perPage" aria-controls="my-table" class="pageing"></b-pagination>
        <b-form-input v-model="productId" placeholder="Product id"></b-form-input>
        <b-form-datepicker class="datepicker" v-model="endDate"></b-form-datepicker>
        <b-button variant="success" @click="search">Search</b-button>
      </div>
          <div class="form-group">
            <p><b>Matinees: </b></p>
            <div
              class="checkbox-group"
            >
              <b-form-checkbox name="check1" class="check" v-model="isChecked">Sat</b-form-checkbox>
              <b-form-checkbox name="check2" class="check" v-model="isChecked">Sun</b-form-checkbox>
              <b-form-checkbox name="check3" class="check" v-model="isChecked">Wed</b-form-checkbox>
              <b-form-checkbox name="check4" class="check" v-model="isChecked">Thu</b-form-checkbox>
              <b-form-checkbox name="check5" class="check" v-model="isChecked">Fri</b-form-checkbox>
            </div>
          </div>
          <div class="form-group">
            <p><b>Evenings: </b></p>
            <div
              class="checkbox-group"
            >
              <b-form-checkbox name="check1" class="check" v-model="isChecked">Fri</b-form-checkbox>
              <b-form-checkbox name="check2" class="check" v-model="isChecked">Sat</b-form-checkbox>
              <b-form-checkbox name="check3" class="check" v-model="isChecked">Tue</b-form-checkbox>
              <b-form-checkbox name="check4" class="check" v-model="isChecked">Wed</b-form-checkbox>
              <b-form-checkbox name="check5" class="check" v-model="isChecked">Thu</b-form-checkbox>
              <b-form-checkbox name="check5" class="check" v-model="isChecked">Sun</b-form-checkbox>
              <b-form-checkbox name="check5" class="check" v-model="isChecked">Mon</b-form-checkbox>
            </div>
          </div>
      <b-table :items="items" :per-page="perPage" :current-page="currentPage" id="my-table"></b-table>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'App',
  components: {
  },
  data() {
    return {
      isChecked: true,
      perPage: 50,
      currentPage: 1,
      startDate: "",
      endDate: "",
      productId: 13800,
      items: [
      ]
    }
  },
  mounted() {
  },
  methods: {
    search() {
      if (this.endDate != "") {
        let dateArr = this.endDate.split("-");
        axios.get("http://127.0.0.1:8000/seats", {
          "params": {
            "pid": this.productId,
            "pyr": dateArr[0], 
            "pmo": dateArr[1],
            "pda": dateArr[2]
          }
        }).then(response => {
          console.log(response);
          this.items = response.data.Seats;
        });
      }
    }
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
.table-wrapper {
  max-width: 1600px;
  margin: auto;
}
.datepicker {
  max-width: 250px;
}
.table-header {
  display: flex;
  align-items: center;
  max-width: 1000px;
  justify-content: space-between;
}
.pageing {
  margin: 0;
}
.checkbox-group {
  display: flex;
}
.form-group {
  display: flex;
}
.check {
  margin-left: 5px;
}
</style>
