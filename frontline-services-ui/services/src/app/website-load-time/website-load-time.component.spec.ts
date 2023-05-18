import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WebsiteLoadTimeComponent } from './website-load-time.component';

describe('WebsiteLoadTimeComponent', () => {
  let component: WebsiteLoadTimeComponent;
  let fixture: ComponentFixture<WebsiteLoadTimeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WebsiteLoadTimeComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(WebsiteLoadTimeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
